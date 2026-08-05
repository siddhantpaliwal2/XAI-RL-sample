#!/usr/bin/env python3
"""Validate and package Opus 5/Fable 5 long-horizon Daytona trials."""

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
TASK = "long-native-table-migration"
SNAPSHOT = "harbor-probe-long-native-table-migration-4g"
AGENT_VERSION = "1.18.13"
DENIED_TASK_CONFIG = json.dumps(
    {"permission": {"task": "deny"}}, separators=(",", ":")
)
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
        "median": percentile(values, 0.5),
        "p90": percentile(values, 0.9),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
    }


def find_trial(job_dir: Path, route: str) -> tuple[Path, dict, dict, dict] | None:
    for result_path in sorted(job_dir.glob("*/result.json")):
        trial_dir = result_path.parent
        try:
            result = json.loads(result_path.read_text())
            trajectory = json.loads((trial_dir / "agent" / "trajectory.json").read_text())
            verifier = json.loads((trial_dir / "verifier" / "output.json").read_text())
        except (OSError, json.JSONDecodeError):
            continue
        reward = ((result.get("verifier_result") or {}).get("rewards") or {}).get("reward")
        agent_config = ((result.get("config") or {}).get("agent") or {})
        environment = ((result.get("config") or {}).get("environment") or {})
        trajectory_agent = trajectory.get("agent") or {}
        if (
            result.get("exception_info") is None
            and reward is not None
            and verifier.get("tests")
            and trajectory.get("steps")
            and agent_config.get("model_name") == route
            and trajectory_agent.get("model_name") == route
            and str(trajectory_agent.get("version")) == AGENT_VERSION
            and (agent_config.get("kwargs") or {}).get("opencode_config")
            == DENIED_TASK_CONFIG
            and (environment.get("kwargs") or {}).get("snapshot_template_name")
            == SNAPSHOT
        ):
            return trial_dir, result, trajectory, verifier
    return None


def package_trial(
    alias: str,
    attempt: int,
    trial_dir: Path,
    result: dict,
    trajectory: dict,
    verifier: dict,
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
    packaged.mkdir(parents=True, exist_ok=True)
    copies = {
        trial_dir / "result.json": packaged / "result.json",
        trial_dir / "agent" / "trajectory.json": packaged / "trajectory.json",
        trial_dir / "verifier" / "output.json": packaged / "verifier-output.json",
        trial_dir / "verifier" / "stdout.txt": packaged / "verifier-stdout.txt",
    }
    for source, destination in copies.items():
        shutil.copy2(source, destination)

    return {
        "task": TASK,
        "attempt": attempt,
        "harness": "opencode",
        "model": MODELS[alias]["label"],
        "route": MODELS[alias]["route"],
        "reward": reward,
        "f2p_passed": sum(statuses.get(name) == "passed" for name in f2p),
        "f2p_total": len(f2p),
        "p2p_passed": sum(statuses.get(name) == "passed" for name in p2p),
        "p2p_total": len(p2p),
        "failed_f2p": [name for name in f2p if statuses.get(name) != "passed"],
        "failed_p2p": [name for name in p2p if statuses.get(name) != "passed"],
        "duration_seconds": seconds_between(result.get("started_at"), result.get("finished_at")),
        "trajectory_steps": len(steps),
        "model_turns": model_turns,
        "tool_calls": tool_calls,
        "input_tokens": agent_result.get("n_input_tokens"),
        "cache_tokens": agent_result.get("n_cache_tokens"),
        "output_tokens": agent_result.get("n_output_tokens"),
        "cost_usd": agent_result.get("cost_usd"),
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
    raw_by_model: dict[str, list[tuple[int, int, tuple]]] = defaultdict(list)
    for run_order, run_id in enumerate(run_ids):
        pattern = re.compile(
            rf"^{re.escape(run_id)}-(opus5|fable5)-{re.escape(TASK)}-a(\d+)$"
        )
        for job_dir in sorted(args.jobs_dir.resolve().glob(f"{run_id}-*")):
            match = pattern.match(job_dir.name)
            if not match:
                continue
            alias, attempt_text = match.groups()
            found = find_trial(job_dir, MODELS[alias]["route"])
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
        },
        "controls": {"null_reward": 0, "oracle_reward": 1},
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
        durations = [
            float(row["duration_seconds"])
            for row in rows
            if row["duration_seconds"] is not None
        ]
        failure_rate = round(failures / len(rows), 4)
        any_model_failure_gate |= failure_rate >= 0.5
        all_tool_calls.extend(tool_calls)
        payload["models"][alias] = {
            "route": model["route"],
            "attempts": len(rows),
            "solves": solves,
            "failures": failures,
            "failure_rate": failure_rate,
            "tool_calls": distribution(tool_calls),
            "model_turns": distribution(turns),
            "duration_seconds": distribution(durations),
            "cost_usd": round(sum((row["cost_usd"] or 0) for row in rows), 4),
            "per_attempt_data": f"long_{alias}_trials.json",
        }
        (SAMPLE_RUN / f"long_{alias}_trials.json").write_text(
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
        "target_tool_calls_per_trial": [70, 100],
        "aggregate_tool_calls": aggregate_tool_calls,
        "median_tool_calls_in_target": bool(
            aggregate_tool_calls["median"] is not None
            and 70 <= aggregate_tool_calls["median"] <= 100
        ),
        "some_model_failure_rate_at_least_50_percent": any_model_failure_gate,
    }
    payload["criteria"]["qualifies"] = bool(
        payload["criteria"]["median_tool_calls_in_target"]
        and any_model_failure_gate
    )
    (SAMPLE_RUN / "long_horizon_results.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
