#!/usr/bin/env python3
"""Validate and package the four-model long-horizon Daytona matrix."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import shutil
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SAMPLE_RUN = ROOT / "sample-run"
INDEXES = SAMPLE_RUN / "indexes"
TASK = "long-native-table-migration"
SNAPSHOT = "harbor-probe-long-native-table-migration-4g"
AGENT_VERSION = "1.18.13"
DENIED_TASK_CONFIG = {"permission": {"task": "deny"}}
MODELS = {
    "opus5": {
        "route": "openrouter/anthropic/claude-opus-5",
        "label": "claude-opus-5",
        "provider": "openrouter",
        "endpoint": "https://openrouter.ai/api/v1",
    },
    "fable5": {
        "route": "openrouter/anthropic/claude-fable-5",
        "label": "claude-fable-5",
        "provider": "openrouter",
        "endpoint": "https://openrouter.ai/api/v1",
    },
    "grok45": {
        "route": "openrouter/x-ai/grok-4.5",
        "label": "grok-4.5",
        "provider": "openrouter",
        "endpoint": "https://openrouter.ai/api/v1",
    },
    "gpt56sol": {
        "route": "openrouter/openai/gpt-5.6-sol",
        "label": "gpt-5.6-sol",
        "provider": "openrouter",
        "endpoint": "https://openrouter.ai/api/v1",
    },
}
DIFFICULTY_GATE_MODELS = {"opus5", "fable5"}
SENSITIVE_ASSIGNMENT = re.compile(
    r"(?im)^(\s*[A-Z_][A-Z0-9_.-]*(?:KEY|SECRET|PASSWORD|TOKEN|CREDENTIAL)"
    r"[A-Z0-9_.-]*\s*=)[^\r\n]*"
)
SENSITIVE_TOKEN_PATTERNS = (
    re.compile(r"sk-or-v1-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/-]{20,}=*"),
)


def directory_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
        digest.update(str(file_path.relative_to(path)).encode())
        digest.update(b"\0")
        digest.update(file_path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def redact_text(value: str) -> str:
    redacted = SENSITIVE_ASSIGNMENT.sub(r"\1<REDACTED>", value)
    for pattern in SENSITIVE_TOKEN_PATTERNS:
        redacted = pattern.sub("<REDACTED>", redacted)
    return redacted


def redact_artifact(value: object) -> object:
    if isinstance(value, dict):
        return {key: redact_artifact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_artifact(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


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
    index = max(math.ceil(fraction * len(ordered)) - 1, 0)
    return round(ordered[index], 3)


def distribution(values: list[float]) -> dict:
    if not values:
        return {"mean": None, "median": None, "p90": None, "min": None, "max": None}
    return {
        "mean": round(sum(values) / len(values), 3),
        "median": round(statistics.median(values), 3),
        "p90": percentile(values, 0.9),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
    }


def pass_at_k(n: int, solves: int, k: int) -> float | None:
    """Unbiased pass@k estimator used by HumanEval and SWE-bench reports."""
    if k < 1 or k > n:
        return None
    if n - solves < k:
        return 1.0
    return round(1 - math.comb(n - solves, k) / math.comb(n, k), 4)


def task_tool_is_denied(value: object) -> bool:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return False
    return value == DENIED_TASK_CONFIG


def find_trial(
    job_dir: Path, route: str, final_task_sha256: str
) -> tuple[Path, Path, dict, dict, dict, str] | None:
    result_paths = sorted(
        job_dir.glob("*/result.json"),
        key=lambda path: (path.parent.name != "recovered-trial", str(path)),
    )
    for result_path in result_paths:
        trial_dir = result_path.parent
        regrade_dir = job_dir / "regrade"
        verifier_dir = (
            regrade_dir
            if (regrade_dir / "output.json").exists()
            else trial_dir / "verifier"
        )
        grading_provenance = (
            "regraded_final_verifier"
            if verifier_dir == regrade_dir
            else "original_harbor_verifier"
        )
        try:
            result = json.loads(result_path.read_text())
            trajectory = json.loads((trial_dir / "agent" / "trajectory.json").read_text())
            verifier = json.loads((verifier_dir / "output.json").read_text())
            metadata = json.loads((job_dir / "matrix-metadata.json").read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if verifier_dir == regrade_dir:
            try:
                reward = float((verifier_dir / "reward.txt").read_text().strip())
            except (OSError, ValueError):
                continue
        else:
            reward = ((result.get("verifier_result") or {}).get("rewards") or {}).get("reward")
        agent_config = ((result.get("config") or {}).get("agent") or {})
        environment = ((result.get("config") or {}).get("environment") or {})
        trajectory_agent = trajectory.get("agent") or {}
        if (
            reward is not None
            and verifier.get("tests")
            and trajectory.get("steps")
            and agent_config.get("model_name") == route
            and trajectory_agent.get("model_name") == route
            and str(trajectory_agent.get("version")) == AGENT_VERSION
            and task_tool_is_denied(
                (agent_config.get("kwargs") or {}).get("opencode_config")
            )
            and (environment.get("kwargs") or {}).get("snapshot_template_name")
            == SNAPSHOT
            and metadata.get("model_route") == route
            and metadata.get("snapshot") == SNAPSHOT
            and str(metadata.get("agent_version")) == AGENT_VERSION
            and metadata.get("task_tool") == "deny"
            and (
                grading_provenance == "regraded_final_verifier"
                or metadata.get("task_sha256") == final_task_sha256
            )
        ):
            normalized_result = copy.deepcopy(result)
            normalized_result["verifier_result"] = {"rewards": {"reward": reward}}
            normalized_result.setdefault("xai_rl_grading", {}).update({
                "provenance": grading_provenance,
                "original_exception_info": result.get("exception_info"),
                "final_task_sha256": final_task_sha256,
            })
            return (
                trial_dir,
                verifier_dir,
                normalized_result,
                trajectory,
                verifier,
                grading_provenance,
            )
    return None


def package_trial(
    alias: str,
    attempt: int,
    trial_dir: Path,
    verifier_dir: Path,
    result: dict,
    trajectory: dict,
    verifier: dict,
    grading_provenance: str,
) -> dict:
    config = json.loads((ROOT / "tasks" / TASK / "tests" / "config.json").read_text())
    statuses = {item["name"]: item["status"] for item in verifier["tests"]}
    f2p = config["fail_to_pass"]
    p2p = config["pass_to_pass"]
    reward = float(result["verifier_result"]["rewards"]["reward"])
    steps = trajectory.get("steps") or []
    model_turns = sum(
        step.get("source") == "agent" and bool(step.get("model_name")) for step in steps
    )
    tool_calls = sum(len(step.get("tool_calls") or []) for step in steps)
    agent_result = result.get("agent_result") or {}

    packaged = SAMPLE_RUN / "long-horizon-trials" / alias / f"attempt-{attempt:02d}"
    if packaged.exists():
        shutil.rmtree(packaged)
    packaged.mkdir(parents=True, exist_ok=True)
    json_artifacts = {
        packaged / "trajectory.json": trajectory,
        packaged / "verifier-output.json": verifier,
        packaged / "result.json": result,
    }
    for destination, artifact in json_artifacts.items():
        destination.write_text(
            json.dumps(redact_artifact(artifact), indent=2) + "\n"
        )
    (packaged / "verifier-stdout.txt").write_text(
        redact_text((verifier_dir / "stdout.txt").read_text())
    )

    return {
        "task": TASK,
        "attempt": attempt,
        "harness": "opencode",
        "model": MODELS[alias]["label"],
        "route": MODELS[alias]["route"],
        "grading_provenance": grading_provenance,
        "reward": reward,
        "f2p_passed": sum(statuses.get(name) == "passed" for name in f2p),
        "f2p_total": len(f2p),
        "p2p_passed": sum(statuses.get(name) == "passed" for name in p2p),
        "p2p_total": len(p2p),
        "failed_f2p": [name for name in f2p if statuses.get(name) != "passed"],
        "failed_p2p": [name for name in p2p if statuses.get(name) != "passed"],
        "duration_seconds": seconds_between(result.get("started_at"), result.get("finished_at")),
        "duration_basis": (result.get("xai_rl_grading") or {}).get(
            "duration_basis", "harbor_started_at_to_finished_at"
        ),
        "trajectory_steps": len(steps),
        "model_turns": model_turns,
        "tool_calls": tool_calls,
        "input_tokens": agent_result.get("n_input_tokens"),
        "cache_tokens": agent_result.get("n_cache_tokens"),
        "output_tokens": agent_result.get("n_output_tokens"),
        "cost_usd": agent_result.get("cost_usd"),
        "artifact_redaction": "credential assignments and bearer tokens redacted",
        "trajectory": str((packaged / "trajectory.json").relative_to(SAMPLE_RUN)),
        "result": str((packaged / "result.json").relative_to(SAMPLE_RUN)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs-dir", type=Path, default=SAMPLE_RUN / "long-raw")
    parser.add_argument(
        "--run-id",
        action="append",
        dest="run_ids",
        help="runner wave to include; repeat to combine staged waves",
    )
    parser.add_argument("--expected-attempts", type=int, required=True)
    args = parser.parse_args()

    run_ids = args.run_ids or ["long-native-r1"]
    final_task_sha256 = directory_sha256(ROOT / "tasks" / TASK)
    raw_by_model: dict[str, list[tuple[int, int, tuple]]] = defaultdict(list)
    for run_order, run_id in enumerate(run_ids):
        aliases = "|".join(map(re.escape, MODELS))
        pattern = re.compile(
            rf"^{re.escape(run_id)}-({aliases})-{re.escape(TASK)}-a(\d+)$"
        )
        for job_dir in sorted(args.jobs_dir.resolve().glob(f"{run_id}-*")):
            match = pattern.match(job_dir.name)
            if not match:
                continue
            alias, attempt_text = match.groups()
            found = find_trial(
                job_dir, MODELS[alias]["route"], final_task_sha256
            )
            if found is not None:
                raw_by_model[alias].append(
                    (run_order, int(attempt_text), found)
                )

    rows_by_model: dict[str, list[dict]] = defaultdict(list)
    for alias in MODELS:
        ordered = sorted(raw_by_model[alias], key=lambda item: (item[0], item[1]))
        for packaged_attempt, (_, _, found) in enumerate(ordered, start=1):
            rows_by_model[alias].append(
                package_trial(alias, packaged_attempt, *found)
            )

    missing = {
        alias: args.expected_attempts - len(rows_by_model[alias])
        for alias in MODELS
        if len(rows_by_model[alias]) != args.expected_attempts
    }
    if missing:
        raise SystemExit(f"incomplete long-horizon matrix: {missing}")

    payload = {
        "task": TASK,
        "provenance": {
            "base_commit": "a03ff50b9e6868565ba88be5f7438f4ac7583138",
            "oracle_commit": "ef9c61f5ae3e5259f8753d000a66a4e18962ffbe",
            "production_commits_condensed": 62,
            "production_files_changed": 70,
            "task_sha256": final_task_sha256,
        },
        "controls": {
            "null_reward": 0,
            "oracle_reward": 1,
            "alternate_field_wiring_reward": 1,
        },
        "agent": {
            "name": "opencode",
            "version": AGENT_VERSION,
            "task_tool": "denied",
            "environment": "daytona-2cpu-4gb-10gb-amd64",
            "snapshot": SNAPSHOT,
        },
        "models": {},
    }
    any_model_failure_gate = False
    all_tool_calls: list[float] = []
    for alias, model in MODELS.items():
        rows = sorted(rows_by_model[alias], key=lambda row: row["attempt"])
        solves = sum(row["reward"] >= 1 for row in rows)
        failures = len(rows) - solves
        tool_calls = [float(row["tool_calls"]) for row in rows]
        turns = [float(row["model_turns"]) for row in rows]
        input_tokens = [
            float(row["input_tokens"])
            for row in rows
            if row["input_tokens"] is not None
        ]
        cache_tokens = [
            float(row["cache_tokens"])
            for row in rows
            if row["cache_tokens"] is not None
        ]
        output_tokens = [
            float(row["output_tokens"])
            for row in rows
            if row["output_tokens"] is not None
        ]
        durations = [
            float(row["duration_seconds"])
            for row in rows
            if row["duration_seconds"] is not None
        ]
        failure_rate = round(failures / len(rows), 4)
        if alias in DIFFICULTY_GATE_MODELS:
            any_model_failure_gate |= failure_rate >= 0.5
        all_tool_calls.extend(tool_calls)
        payload["models"][alias] = {
            "route": model["route"],
            "provider": model["provider"],
            "endpoint": model["endpoint"],
            "attempts": len(rows),
            "solves": solves,
            "failures": failures,
            "failure_rate": failure_rate,
            "pass_at_k": {
                f"pass@{k}": pass_at_k(len(rows), solves, k)
                for k in range(1, min(3, len(rows)) + 1)
            },
            "tool_calls": distribution(tool_calls),
            "model_turns": distribution(turns),
            "input_tokens": {
                "total": int(sum(input_tokens)),
                **distribution(input_tokens),
            },
            "cache_tokens": {
                "total": int(sum(cache_tokens)),
                **distribution(cache_tokens),
            },
            "output_tokens": {
                "total": int(sum(output_tokens)),
                **distribution(output_tokens),
            },
            "duration_seconds": distribution(durations),
            "cost_usd": round(sum((row["cost_usd"] or 0) for row in rows), 4),
            "per_attempt_data": f"long_{alias}_trials.json",
        }
        INDEXES.mkdir(parents=True, exist_ok=True)
        (INDEXES / f"long_{alias}_trials.json").write_text(
            json.dumps(rows, indent=2) + "\n"
        )

        best = max(
            rows,
            key=lambda row: (row["reward"], row["f2p_passed"], -row["attempt"]),
        )
        representative = (
            SAMPLE_RUN
            / "trajectories-matrix"
            / f"{TASK}--opencode--{model['label']}"
            f"{'--SOLVED' if best['reward'] >= 1 else ''}.trajectory.json"
        )
        shutil.copy2(SAMPLE_RUN / best["trajectory"], representative)

    aggregate_tool_calls = distribution(all_tool_calls)
    payload["criteria"] = {
        "tool_call_reference_band": [70, 100],
        "aggregate_tool_calls": aggregate_tool_calls,
        "median_tool_calls_in_reference_band": bool(
            aggregate_tool_calls["median"] is not None
            and 70 <= aggregate_tool_calls["median"] <= 100
        ),
        "tool_call_reference_is_hard_gate": False,
        "difficulty_gate_models": sorted(DIFFICULTY_GATE_MODELS),
        "opus_or_fable_failure_rate_at_least_50_percent": any_model_failure_gate,
    }
    payload["criteria"]["qualifies"] = bool(any_model_failure_gate)
    (INDEXES / "long_horizon_results.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
