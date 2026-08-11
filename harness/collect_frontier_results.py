#!/usr/bin/env python3
"""Package Opus 5/Fable 5 Daytona trials and update the pass@k matrix."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SAMPLE_RUN = ROOT / "sample-run"
INDEXES = SAMPLE_RUN / "indexes"
CONTROLS = SAMPLE_RUN / "controls"
MODELS = {
    "opus5": {
        "route": "openrouter/anthropic/claude-opus-5",
        "label": "claude-opus-5",
    },
    "fable5": {
        "route": "openrouter/anthropic/claude-fable-5",
        "label": "claude-fable-5",
    },
}
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


def find_valid_trial(job_dir: Path, expected_route: str) -> tuple[Path, dict, dict] | None:
    for result_path in sorted(job_dir.glob("*/result.json")):
        try:
            result = json.loads(result_path.read_text())
            trajectory = json.loads(
                (result_path.parent / "agent" / "trajectory.json").read_text()
            )
            verifier = json.loads(
                (result_path.parent / "verifier" / "output.json").read_text()
            )
        except (OSError, json.JSONDecodeError):
            continue
        reward = ((result.get("verifier_result") or {}).get("rewards") or {}).get(
            "reward"
        )
        result_route = (((result.get("config") or {}).get("agent") or {}).get("model_name"))
        trajectory_agent = trajectory.get("agent") or {}
        if (
            result.get("exception_info") is None
            and reward is not None
            and verifier.get("tests")
            and trajectory.get("steps")
            and result_route == expected_route
            and trajectory_agent.get("model_name") == expected_route
            and str(trajectory_agent.get("version")) == "1.18.13"
        ):
            return result_path.parent, result, trajectory
    return None


def tool_call_count(trajectory: dict) -> int:
    return sum(len(step.get("tool_calls") or []) for step in trajectory.get("steps") or [])


def model_turn_count(trajectory: dict) -> int:
    return sum(
        step.get("source") == "agent" and bool(step.get("model_name"))
        for step in trajectory.get("steps") or []
    )


def package_trial(
    alias: str,
    task: str,
    attempt: int,
    trial_dir: Path,
    result: dict,
    trajectory: dict,
) -> dict:
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

    packaged = SAMPLE_RUN / "frontier-trials" / alias / task / f"attempt-{attempt:02d}"
    packaged.mkdir(parents=True, exist_ok=True)
    copies = {
        trial_dir / "result.json": packaged / "result.json",
        trial_dir / "agent" / "trajectory.json": packaged / "trajectory.json",
        verifier_path: packaged / "verifier-output.json",
        trial_dir / "verifier" / "stdout.txt": packaged / "verifier-stdout.txt",
    }
    for source, destination in copies.items():
        shutil.copy2(source, destination)

    return {
        "task": task,
        "attempt": attempt,
        "harness": "opencode",
        "model": MODELS[alias]["label"],
        "route": MODELS[alias]["route"],
        "provider": "openrouter",
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


def parse_smoke(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("smokes must use ALIAS=PATH")
    alias, raw_path = value.split("=", 1)
    if alias not in MODELS:
        raise argparse.ArgumentTypeError(f"unknown smoke model alias: {alias}")
    return alias, Path(raw_path)


def parse_supplement(value: str) -> tuple[str, str, int, Path]:
    """Parse ALIAS:TASK:ATTEMPT=PATH for a compatibility rerun."""
    if "=" not in value:
        raise argparse.ArgumentTypeError("supplements must use ALIAS:TASK:ATTEMPT=PATH")
    identity, raw_path = value.split("=", 1)
    parts = identity.split(":")
    if len(parts) != 3 or parts[0] not in MODELS or parts[1] not in TASKS:
        raise argparse.ArgumentTypeError(f"invalid supplement identity: {identity}")
    try:
        attempt = int(parts[2])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("supplement attempt must be an integer") from exc
    return parts[0], parts[1], attempt, Path(raw_path)


def parse_exclusion(value: str) -> tuple[str, str, Path]:
    """Parse ALIAS:TASK=PATH for a route/provider exclusion artifact."""
    if "=" not in value:
        raise argparse.ArgumentTypeError("exclusions must use ALIAS:TASK=PATH")
    identity, raw_path = value.split("=", 1)
    parts = identity.split(":")
    if len(parts) != 2 or parts[0] not in MODELS or parts[1] not in TASKS:
        raise argparse.ArgumentTypeError(f"invalid exclusion identity: {identity}")
    return parts[0], parts[1], Path(raw_path)


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = math.ceil(fraction * len(ordered)) - 1
    return round(ordered[max(index, 0)], 3)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs-dir", type=Path, default=SAMPLE_RUN / "frontier-raw")
    parser.add_argument("--run-id", default="existing8-r1")
    parser.add_argument("--expected-attempts", type=int, default=1)
    parser.add_argument("--smoke", action="append", type=parse_smoke, default=[])
    parser.add_argument("--supplement", action="append", type=parse_supplement, default=[])
    parser.add_argument("--exclusion", action="append", type=parse_exclusion, default=[])
    args = parser.parse_args()

    rows_by_model: dict[str, list[dict]] = defaultdict(list)
    seen: set[tuple[str, str, int]] = set()
    pattern = re.compile(
        rf"^{re.escape(args.run_id)}-(opus5|fable5)-(.+)-a(\d{{2}})$"
    )
    for job_dir in sorted(args.jobs_dir.resolve().glob(f"{args.run_id}-*-a??")):
        match = pattern.match(job_dir.name)
        if not match:
            continue
        alias, task, attempt_text = match.groups()
        attempt = int(attempt_text)
        if task not in TASKS:
            continue
        found = find_valid_trial(job_dir, MODELS[alias]["route"])
        if found is None:
            continue
        key = (alias, task, attempt)
        if key in seen:
            raise SystemExit(f"duplicate trial: {key}")
        seen.add(key)
        trial_dir, result, trajectory = found
        rows_by_model[alias].append(
            package_trial(alias, task, attempt, trial_dir, result, trajectory)
        )

    exclusion_keys: set[tuple[str, str]] = set()
    exclusions: list[dict] = []
    for alias, task, exclusion_dir in args.exclusion:
        exclusion_keys.add((alias, task))
        candidates = sorted(exclusion_dir.expanduser().resolve().rglob("result.json"))
        trial_result_path = next(
            (
                path
                for path in candidates
                if json.loads(path.read_text()).get("task_name") == task
            ),
            None,
        )
        if trial_result_path is None:
            raise SystemExit(f"missing exclusion result for {alias}/{task}: {exclusion_dir}")
        trial_dir = trial_result_path.parent
        result = json.loads(trial_result_path.read_text())
        packaged = SAMPLE_RUN / "frontier-exclusions" / f"{alias}-{task}"
        packaged.mkdir(parents=True, exist_ok=True)
        copies = {
            trial_result_path: packaged / "result.json",
            trial_dir / "agent" / "trajectory.json": packaged / "trajectory.json",
            trial_dir / "agent" / "opencode.txt": packaged / "opencode.txt",
            trial_dir / "exception.txt": packaged / "exception.txt",
        }
        for source, destination in copies.items():
            if source.is_file():
                shutil.copy2(source, destination)
        exception = result.get("exception_info") or {}
        opencode_text = (trial_dir / "agent" / "opencode.txt").read_text(
            errors="replace"
        )
        exclusions.append(
            {
                "model": alias,
                "task": task,
                "reason": "provider_content_filter",
                "provider_error": (
                    "ContentFilterError"
                    if "ContentFilterError" in opencode_text
                    else None
                ),
                "exception_type": exception.get("exception_type"),
                "artifact_dir": str(packaged.relative_to(SAMPLE_RUN)),
                "counted_as_model_result": False,
            }
        )

    for alias, smoke_dir in args.smoke:
        task = "latent-credit-normalize"
        key = (alias, task, 1)
        if key in seen:
            continue
        found = find_valid_trial(smoke_dir.expanduser().resolve(), MODELS[alias]["route"])
        if found is None:
            raise SystemExit(f"invalid smoke trial for {alias}: {smoke_dir}")
        seen.add(key)
        trial_dir, result, trajectory = found
        rows_by_model[alias].append(
            package_trial(alias, task, 1, trial_dir, result, trajectory)
        )

    for alias, task, attempt, supplement_dir in args.supplement:
        key = (alias, task, attempt)
        if key in seen:
            continue
        found = find_valid_trial(
            supplement_dir.expanduser().resolve(), MODELS[alias]["route"]
        )
        if found is None:
            raise SystemExit(
                f"invalid supplement for {alias}/{task}/attempt-{attempt:02d}: "
                f"{supplement_dir}"
            )
        seen.add(key)
        trial_dir, result, trajectory = found
        rows_by_model[alias].append(
            package_trial(alias, task, attempt, trial_dir, result, trajectory)
        )

    missing: dict[str, dict[str, int]] = {}
    for alias in MODELS:
        counts = defaultdict(int)
        for row in rows_by_model[alias]:
            counts[row["task"]] += 1
        model_missing = {
            task: args.expected_attempts - counts[task]
            for task in TASKS
            if counts[task] != args.expected_attempts and (alias, task) not in exclusion_keys
        }
        if model_missing:
            missing[alias] = model_missing
    if missing:
        raise SystemExit(f"incomplete matrix: {missing}")

    INDEXES.mkdir(parents=True, exist_ok=True)
    CONTROLS.mkdir(parents=True, exist_ok=True)
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
            }
            summaries.append(summary)
            matrix[f"opencode|{model['label']}|{task}"] = {
                "n": n,
                "c": c,
                "pass@1": summary["pass@1"],
                "pass@3": summary["pass@3"],
                "pass@10": summary["pass@10"],
            }

            target_dir = SAMPLE_RUN / "trajectories-matrix"
            for old in target_dir.glob(f"{task}--opencode--{model['label']}*.trajectory.json"):
                old.unlink()
            if task_rows:
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
                    target_dir / f"{task}--opencode--{model['label']}{solved}.trajectory.json",
                )

        durations = [row["duration_seconds"] for row in rows if row["duration_seconds"] is not None]
        measured_pass1 = [item["pass@1"] for item in summaries if item["pass@1"] is not None]
        totals = {
            "attempts": len(rows),
            "solves": sum(row["reward"] >= 1 for row in rows),
            "mean_pass@1": round(sum(measured_pass1) / len(measured_pass1), 4),
            "cost_usd": round(sum((row["cost_usd"] or 0) for row in rows), 4),
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
            "model": model["route"],
            "harness": "opencode-1.18.13",
            "environment": "daytona-2cpu-4gb-amd64",
            "attempts_per_task": args.expected_attempts,
            "tasks": summaries,
            "totals": totals,
            "per_attempt_data": f"{alias}_trials.json",
        }
        (INDEXES / f"{alias}_trials.json").write_text(json.dumps(rows, indent=2) + "\n")
        (INDEXES / f"{alias}_results.json").write_text(json.dumps(payload, indent=2) + "\n")
        all_results[alias] = payload

    matrix_path.write_text(json.dumps(matrix, indent=1) + "\n")
    (CONTROLS / "frontier_exclusions.json").write_text(
        json.dumps(exclusions, indent=2) + "\n"
    )
    print(json.dumps(all_results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
