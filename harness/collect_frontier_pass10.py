#!/usr/bin/env python3
"""Merge the original screen with completion trials into an audited pass@10.

The original Opus 5 and Fable 5 screen used one OpenRouter attempt per
available task cell. The completion run adds nine further valid attempts per
available cell, primarily on Bedrock. Fable/FIU remains excluded because both
providers consistently filter the task before verification. Every completion
trial is checked against its requested route, OpenCode version, Daytona
snapshot, task checksum, and the model name recorded on every trajectory step
before it is packaged.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from run_frontier_daytona import (
    TASK_SNAPSHOTS,
    directory_sha256,
    trial_artifacts,
    valid_existing,
)


ROOT = Path(__file__).resolve().parent.parent
SAMPLE_RUN = ROOT / "sample-run"
INDEXES = SAMPLE_RUN / "indexes"
TASKS = [
    "latent-credit-normalize",
    "latent-doc-extractors",
    "latent-financial-tools",
    "latent-phone-invites",
    "xrepo-fiu-latent",
    "xrepo-txenrich-latent",
    "xrepo-txenrich3-latent",
    "xrepo-txenrich4-latent",
]
MODELS = {
    "opus5": {
        "label": "claude-opus-5",
        "openrouter_route": "openrouter/anthropic/claude-opus-5",
        "bedrock_routes": ["amazon-bedrock/global.anthropic.claude-opus-5"],
    },
    "fable5": {
        "label": "claude-fable-5",
        "openrouter_route": "openrouter/anthropic/claude-fable-5",
        "bedrock_routes": [
            "amazon-bedrock/global.anthropic.claude-fable-5",
            "amazon-bedrock/us.anthropic.claude-fable-5",
        ],
    },
}
EXCLUDED_CELLS = {("fable5", "xrepo-fiu-latent"): "provider_content_filter"}
PROVIDER_LIMITED_CELLS = {
    ("fable5", "latent-doc-extractors"): "provider_content_filter_after_n3",
}


def pass_at_k(n: int, c: int, k: int) -> float | None:
    if n < k:
        return None
    if n - c < k:
        return 1.0
    return round(1.0 - math.comb(n - c, k) / math.comb(n, k), 4)


def seconds_between(started: str | None, finished: str | None) -> float | None:
    if not started or not finished:
        return None
    start = datetime.fromisoformat(started.replace("Z", "+00:00"))
    finish = datetime.fromisoformat(finished.replace("Z", "+00:00"))
    return round((finish - start).total_seconds(), 3)


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = math.ceil(fraction * len(ordered)) - 1
    return round(ordered[max(index, 0)], 3)


def tool_call_count(trajectory: dict) -> int:
    return sum(
        len(step.get("tool_calls") or []) for step in trajectory.get("steps") or []
    )


def model_turn_count(trajectory: dict) -> int:
    return sum(
        step.get("source") == "agent" and bool(step.get("model_name"))
        for step in trajectory.get("steps") or []
    )


def validate_baseline(alias: str, rows: list[dict]) -> list[dict]:
    model = MODELS[alias]
    expected_tasks = set(TASKS)
    if alias == "fable5":
        expected_tasks.remove("xrepo-fiu-latent")
    found_tasks = [row.get("task") for row in rows]
    if set(found_tasks) != expected_tasks or len(found_tasks) != len(expected_tasks):
        raise SystemExit(f"invalid {alias} OpenRouter baseline tasks: {found_tasks}")

    normalized = []
    for row in rows:
        if (
            row.get("provider") != "openrouter"
            or row.get("route") != model["openrouter_route"]
            or row.get("attempt") != 1
        ):
            raise SystemExit(f"invalid {alias} OpenRouter baseline row: {row}")
        trajectory_path = SAMPLE_RUN / row["trajectory"]
        result_path = SAMPLE_RUN / row["result"]
        if not trajectory_path.is_file() or not result_path.is_file():
            raise SystemExit(f"missing baseline artifacts for {alias}/{row['task']}")
        trajectory = json.loads(trajectory_path.read_text())
        step_models = {
            step.get("model_name")
            for step in trajectory.get("steps") or []
            if step.get("model_name")
        }
        if trajectory.get("agent", {}).get("model_name") != model["openrouter_route"]:
            raise SystemExit(f"baseline trajectory route mismatch: {trajectory_path}")
        if step_models != {model["openrouter_route"]}:
            raise SystemExit(f"baseline step route mismatch: {trajectory_path}")
        item = dict(row)
        item.update(
            {
                "provider_attempt": 1,
                "attempt_uid": "openrouter-01",
                "fallback_disabled": None,
                "provider_data_share": None,
            }
        )
        normalized.append(item)
    return normalized


def validate_no_fallback_events(trial_dir: Path) -> None:
    output_path = trial_dir / "agent" / "opencode.txt"
    if not output_path.is_file():
        raise SystemExit(f"missing OpenCode output: {output_path}")
    for line_number, line in enumerate(output_path.read_text(errors="replace").splitlines(), 1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        part = event.get("part") if isinstance(event, dict) else None
        if event.get("type") == "fallback" or (
            isinstance(part, dict) and part.get("type") == "fallback"
        ):
            raise SystemExit(f"fallback event in {output_path}:{line_number}")


def package_completion_trial(
    alias: str,
    task: str,
    provider_attempt: int,
    combined_attempt: int,
    trial_dir: Path,
    result: dict,
    trajectory: dict,
) -> dict:
    route = trajectory.get("agent", {}).get("model_name")
    allowed_routes = {
        MODELS[alias]["openrouter_route"],
        *MODELS[alias]["bedrock_routes"],
    }
    if route not in allowed_routes:
        raise SystemExit(f"unapproved completion route in {trial_dir}: {route}")
    step_models = {
        step.get("model_name")
        for step in trajectory.get("steps") or []
        if step.get("model_name")
    }
    if trajectory.get("agent", {}).get("model_name") != route:
        raise SystemExit(f"trajectory route mismatch: {trial_dir}")
    if step_models != {route}:
        raise SystemExit(f"step route mismatch in {trial_dir}: {sorted(step_models)}")
    validate_no_fallback_events(trial_dir)

    config = json.loads((ROOT / "tasks" / task / "tests" / "config.json").read_text())
    verifier_path = trial_dir / "verifier" / "output.json"
    verifier = json.loads(verifier_path.read_text())
    statuses = {item["name"]: item["status"] for item in verifier["tests"]}
    fail_to_pass = config["fail_to_pass"]
    pass_to_pass = config["pass_to_pass"]
    f2p_passed = sum(statuses.get(name) == "passed" for name in fail_to_pass)
    p2p_passed = sum(statuses.get(name) == "passed" for name in pass_to_pass)
    reward = float(result["verifier_result"]["rewards"]["reward"])
    agent_result = result.get("agent_result") or {}

    packaged = (
        SAMPLE_RUN
        / "frontier-trials"
        / alias
        / task
        / f"attempt-{combined_attempt:02d}"
    )
    packaged.mkdir(parents=True, exist_ok=True)
    copies = {
        trial_dir / "result.json": packaged / "result.json",
        trial_dir / "agent" / "trajectory.json": packaged / "trajectory.json",
        verifier_path: packaged / "verifier-output.json",
        trial_dir / "verifier" / "stdout.txt": packaged / "verifier-stdout.txt",
    }
    for source, destination in copies.items():
        if not source.is_file():
            raise SystemExit(f"missing trial artifact: {source}")
        shutil.copy2(source, destination)

    provider = route.split("/", 1)[0]
    return {
        "task": task,
        "attempt": combined_attempt,
        "provider_attempt": provider_attempt,
        "attempt_uid": f"{provider}-{provider_attempt:02d}",
        "harness": "opencode",
        "model": MODELS[alias]["label"],
        "route": route,
        "provider": provider,
        "fallback_disabled": True,
        "provider_data_share": alias == "fable5" and provider == "amazon-bedrock",
        "reward": reward,
        "f2p_passed": f2p_passed,
        "f2p_total": len(fail_to_pass),
        "p2p_passed": p2p_passed,
        "p2p_total": len(pass_to_pass),
        "failed_f2p": [name for name in fail_to_pass if statuses.get(name) != "passed"],
        "failed_p2p": [name for name in pass_to_pass if statuses.get(name) != "passed"],
        "duration_seconds": seconds_between(result.get("started_at"), result.get("finished_at")),
        "trajectory_steps": len(trajectory.get("steps") or []),
        "model_turns": model_turn_count(trajectory),
        "tool_calls": tool_call_count(trajectory),
        "input_tokens": agent_result.get("n_input_tokens"),
        "cache_tokens": agent_result.get("n_cache_tokens"),
        "output_tokens": agent_result.get("n_output_tokens"),
        "cost_usd": agent_result.get("cost_usd"),
        "trajectory": str((packaged / "trajectory.json").relative_to(SAMPLE_RUN)),
        "result": str((packaged / "result.json").relative_to(SAMPLE_RUN)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--jobs-dir", type=Path, default=SAMPLE_RUN / "bedrock-smoke-raw"
    )
    parser.add_argument("--run-id", default="bedrock-smoke-r1")
    parser.add_argument("--expected-attempts", type=int, default=10)
    parser.add_argument("--agent-version", default="1.18.13")
    args = parser.parse_args()

    rows_by_model: dict[str, list[dict]] = {}
    for alias in MODELS:
        baseline_path = INDEXES / f"{alias}_trials.json"
        baseline = validate_baseline(alias, json.loads(baseline_path.read_text()))
        rows_by_model[alias] = baseline

    pattern = re.compile(
        rf"^{re.escape(args.run_id)}-(opus5|fable5)-(.+)-a(\d+)$"
    )
    seen_completion: set[tuple[str, str, int]] = set()
    completion_candidates: dict[tuple[str, str], list[tuple[int, Path, dict, dict]]] = (
        defaultdict(list)
    )
    for job_dir in sorted(args.jobs_dir.resolve().glob(f"{args.run_id}-*-a*")):
        match = pattern.match(job_dir.name)
        if not match:
            continue
        alias, task, attempt_text = match.groups()
        if task not in TASKS:
            continue
        provider_attempt = int(attempt_text)
        key = (alias, task, provider_attempt)
        if key in seen_completion:
            raise SystemExit(f"duplicate completion trial: {key}")
        try:
            route = json.loads((job_dir / "matrix-metadata.json").read_text())[
                "model_route"
            ]
        except (OSError, KeyError, json.JSONDecodeError):
            continue
        allowed_routes = {
            MODELS[alias]["openrouter_route"],
            *MODELS[alias]["bedrock_routes"],
        }
        if route not in allowed_routes:
            continue
        valid = valid_existing(
            job_dir,
            route=route,
            snapshot=TASK_SNAPSHOTS[task],
            agent_version=args.agent_version,
            checksum=directory_sha256(ROOT / "tasks" / task),
            disable_task_tool=False,
        )
        if valid is None:
            continue
        found = trial_artifacts(job_dir)
        if found is None:
            continue
        trial_dir, result, trajectory = found
        completion_candidates[(alias, task)].append(
            (provider_attempt, trial_dir, result, trajectory)
        )
        seen_completion.add(key)

    missing: dict[str, dict[str, int]] = {}
    for alias, rows in rows_by_model.items():
        model_missing = {}
        for task in TASKS:
            if (alias, task) in EXCLUDED_CELLS:
                continue
            baseline_count = sum(row["task"] == task for row in rows)
            needed = args.expected_attempts - baseline_count
            available = len(completion_candidates[(alias, task)])
            if (alias, task) in PROVIDER_LIMITED_CELLS:
                continue
            if available < needed:
                model_missing[task] = needed - available
        if model_missing:
            missing[alias] = model_missing
    if missing:
        raise SystemExit(f"incomplete pass@10 matrix: {missing}")

    # Infrastructure retries can leave gaps in provider attempt numbers. Select
    # the first required valid completion jobs and number only valid model trials
    # contiguously in the combined denominator.
    for alias, rows in rows_by_model.items():
        for task in TASKS:
            if (alias, task) in EXCLUDED_CELLS:
                continue
            baseline_count = sum(row["task"] == task for row in rows)
            needed = args.expected_attempts - baseline_count
            candidates = sorted(
                completion_candidates[(alias, task)], key=lambda item: item[0]
            )[:needed]
            for valid_index, (
                provider_attempt,
                trial_dir,
                result,
                trajectory,
            ) in enumerate(candidates, start=1):
                rows.append(
                    package_completion_trial(
                        alias,
                        task,
                        provider_attempt,
                        baseline_count + valid_index,
                        trial_dir,
                        result,
                        trajectory,
                    )
                )

    INDEXES.mkdir(parents=True, exist_ok=True)
    matrix_path = INDEXES / "passk_matrix.json"
    matrix = json.loads(matrix_path.read_text())
    all_results: dict[str, dict] = {}
    for alias, model in MODELS.items():
        rows = sorted(
            rows_by_model[alias], key=lambda row: (TASKS.index(row["task"]), row["attempt"])
        )
        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            grouped[row["task"]].append(row)

        summaries = []
        for task in TASKS:
            task_rows = grouped[task]
            n = len(task_rows)
            c = sum(row["reward"] >= 1 for row in task_rows)
            summary = {
                "task": task,
                "n": n,
                "c": c,
                "pass@1": pass_at_k(n, c, 1),
                "pass@3": pass_at_k(n, c, 3),
                "pass@10": pass_at_k(n, c, 10),
                "provider_attempts": dict(Counter(row["provider"] for row in task_rows)),
            }
            if (alias, task) in EXCLUDED_CELLS:
                summary["excluded"] = True
                summary["exclusion_reason"] = EXCLUDED_CELLS[(alias, task)]
            if (alias, task) in PROVIDER_LIMITED_CELLS:
                summary["provider_limited"] = True
                summary["provider_limitation_reason"] = PROVIDER_LIMITED_CELLS[
                    (alias, task)
                ]
            summaries.append(summary)
            matrix[f"opencode|{model['label']}|{task}"] = {
                key: summary[key] for key in ("n", "c", "pass@1", "pass@3", "pass@10")
            }

            target_dir = SAMPLE_RUN / "trajectories-matrix"
            for old in target_dir.glob(
                f"{task}--opencode--{model['label']}*.trajectory.json"
            ):
                old.unlink()
            if not task_rows:
                continue
            best = max(
                task_rows,
                key=lambda row: (
                    row["reward"],
                    row["f2p_passed"],
                    row["p2p_passed"],
                    -row["attempt"],
                ),
            )
            solved = "--SOLVED" if best["reward"] >= 1 else ""
            shutil.copy2(
                SAMPLE_RUN / best["trajectory"],
                target_dir
                / f"{task}--opencode--{model['label']}{solved}.trajectory.json",
            )

        durations = [
            row["duration_seconds"]
            for row in rows
            if row.get("duration_seconds") is not None
        ]
        cost_by_provider: dict[str, float] = defaultdict(float)
        for row in rows:
            cost_by_provider[row["provider"]] += row.get("cost_usd") or 0
        measured_by_k = {
            metric: [item for item in summaries if item[metric] is not None]
            for metric in ("pass@1", "pass@3", "pass@10")
        }
        totals = {
            "attempts": len(rows),
            "solves": sum(row["reward"] >= 1 for row in rows),
            "macro_pass@1": round(
                sum(item["pass@1"] for item in measured_by_k["pass@1"])
                / len(measured_by_k["pass@1"]),
                4,
            ),
            "macro_pass@3": round(
                sum(item["pass@3"] for item in measured_by_k["pass@3"])
                / len(measured_by_k["pass@3"]),
                4,
            ),
            "macro_pass@10": round(
                sum(item["pass@10"] for item in measured_by_k["pass@10"])
                / len(measured_by_k["pass@10"]),
                4,
            ),
            "macro_task_counts": {
                metric: len(items) for metric, items in measured_by_k.items()
            },
            "cost_usd": round(sum(cost_by_provider.values()), 4),
            "cost_usd_by_provider": {
                provider: round(cost, 4)
                for provider, cost in sorted(cost_by_provider.items())
            },
            "attempts_by_provider": dict(Counter(row["provider"] for row in rows)),
            "model_turns": sum(row["model_turns"] for row in rows),
            "tool_calls": sum(row["tool_calls"] for row in rows),
            "duration_seconds": {
                "mean": round(sum(durations) / len(durations), 3),
                "median": percentile(durations, 0.5),
                "p90": percentile(durations, 0.9),
                "min": round(min(durations), 3),
                "max": round(max(durations), 3),
            },
        }
        payload = {
            "model": model["label"],
            "routes": [model["openrouter_route"], *model["bedrock_routes"]],
            "harness": "opencode-1.18.13",
            "environment": "daytona-2cpu-4gb-amd64",
            "target_attempts_per_available_task": args.expected_attempts,
            "methodology": (
                "Original OpenRouter attempt plus validated completion attempts, "
                "primarily on Bedrock; "
                "only trials with real verifier verdicts enter n. Fable/FIU remains "
                "excluded after consistent OpenRouter and Bedrock content filters; "
                "Fable/doc remains provider-limited at n=3 after a bounded exact-"
                "harness retry sweep across both providers."
            ),
            "tasks": summaries,
            "totals": totals,
            "per_attempt_data": f"{alias}_trials.json",
        }
        (INDEXES / f"{alias}_trials.json").write_text(
            json.dumps(rows, indent=2) + "\n"
        )
        (INDEXES / f"{alias}_results.json").write_text(
            json.dumps(payload, indent=2) + "\n"
        )
        all_results[alias] = payload

    matrix_path.write_text(json.dumps(matrix, indent=1) + "\n")
    print(json.dumps(all_results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
