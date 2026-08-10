#!/usr/bin/env python3
"""Package and summarize the final XAI long-horizon enterprise cohort."""

from __future__ import annotations

import json
import math
import shutil
import hashlib
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from collect_enterprise_results import redact_artifact, redact_text
from run_enterprise_daytona import TASK_SNAPSHOTS, complete_existing, recorded_spend
from run_frontier_daytona import directory_sha256


ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "sample-run" / "enterprise-raw"
PACKAGED = ROOT / "sample-run" / "long-horizon-enterprise-trials"
OUTPUT = ROOT / "sample-run" / "long-horizon-enterprise-results.json"
MANIFEST = ROOT / "sample-run" / "long-horizon-enterprise-artifacts-manifest.json"
LEDGER = ROOT / "sample-run" / "enterprise-budget-ledger.jsonl"
AGENT_VERSION = "1.18.13"

TASKS = (
    "paigo-customer-billing-schedule-migration",
    "paigo-top-up-billing-lifecycle",
    "paigo-s3-datastore-measurement",
)

TASK_METADATA = {
    "paigo-customer-billing-schedule-migration": {
        "label": "Billing-schedule migration",
        "change_family": "billing and identity migration",
        "oracle_files": 23,
        "changed_loc": 343,
        "original_developers": 2,
        "historical_implementation_days": 4,
        "ticket_activity_days": None,
        "estimated_human_solve_days": 3,
    },
    "paigo-top-up-billing-lifecycle": {
        "label": "Top-up billing lifecycle",
        "change_family": "wallet and billing lifecycle",
        "oracle_files": 28,
        "changed_loc": 1450,
        "original_developers": 1,
        "historical_implementation_days": 6,
        "ticket_activity_days": 18.5,
        "estimated_human_solve_days": 3,
    },
    "paigo-s3-datastore-measurement": {
        "label": "S3 datastore measurement",
        "change_family": "AWS usage-ingestion feature",
        "oracle_files": 17,
        "changed_loc": 1809,
        "original_developers": 1,
        "historical_implementation_days": 3,
        "ticket_activity_days": 17.8,
        "estimated_human_solve_days": 5,
        "loc_note": "Changed LOC includes a dependency lockfile.",
    },
}


def numbered_jobs(prefix: str, task: str, start: int, end: int) -> list[str]:
    return [f"{prefix}-{task}-a{attempt:02d}" for attempt in range(start, end + 1)]


SUPERSEDED_BILLING_OPUS_JOBS = [
    "enterprise-opus-final-taxonomy-r1-opus5-bedrock-"
    "paigo-customer-billing-schedule-migration-a01",
    *numbered_jobs(
        "enterprise-opus-final-a23-r1-opus5-bedrock",
        "paigo-customer-billing-schedule-migration",
        2,
        3,
    ),
    *numbered_jobs(
        "enterprise-opus-final-a48-r1-opus5-bedrock",
        "paigo-customer-billing-schedule-migration",
        4,
        8,
    ),
]

SUPERSEDED_BILLING_GROK_JOBS = [
    *numbered_jobs(
        "enterprise-corrected-grok4-r1-grok45",
        "paigo-customer-billing-schedule-migration",
        1,
        4,
    ),
    *numbered_jobs(
        "enterprise-final8-grok-r1-grok45",
        "paigo-customer-billing-schedule-migration",
        5,
        8,
    ),
]

MODEL_SPECS = {
    "grok45": {
        "model": "Grok 4.5",
        "route": "openrouter/x-ai/grok-4.5",
        "jobs": {
            task: (
                numbered_jobs(
                    "enterprise-billing-fair-final8-grok-r1-grok45",
                    task,
                    1,
                    8,
                )
                if task == "paigo-customer-billing-schedule-migration"
                else [
                    *numbered_jobs("enterprise-corrected-grok4-r1-grok45", task, 1, 4),
                    *numbered_jobs("enterprise-final8-grok-r1-grok45", task, 5, 8),
                ]
            )
            for task in TASKS
        },
    },
    "opus5": {
        "model": "Claude Opus 5",
        "route": "amazon-bedrock/global.anthropic.claude-opus-5",
        "jobs": {
            "paigo-customer-billing-schedule-migration": numbered_jobs(
                "enterprise-billing-fair-final8-opus-r1-opus5-bedrock",
                "paigo-customer-billing-schedule-migration",
                1,
                8,
            ),
            "paigo-top-up-billing-lifecycle": [
                *numbered_jobs(
                    "enterprise-fairness-v3-r1-opus5-bedrock",
                    "paigo-top-up-billing-lifecycle",
                    1,
                    4,
                ),
                *numbered_jobs(
                    "enterprise-final8-opus-r1-opus5-bedrock",
                    "paigo-top-up-billing-lifecycle",
                    5,
                    8,
                ),
            ],
            "paigo-s3-datastore-measurement": [
                *numbered_jobs(
                    "enterprise-fairness-v4-s3-r1-opus5-bedrock",
                    "paigo-s3-datastore-measurement",
                    1,
                    4,
                ),
                *numbered_jobs(
                    "enterprise-final8-opus-r1-opus5-bedrock",
                    "paigo-s3-datastore-measurement",
                    5,
                    8,
                ),
            ],
        },
    },
}


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def seconds_between(start: str, finish: str) -> float:
    return round((parse_timestamp(finish) - parse_timestamp(start)).total_seconds(), 3)


def wilson_interval(solves: int, attempts: int, z: float = 1.959963984540054) -> list[float]:
    if attempts == 0:
        return [0.0, 0.0]
    proportion = solves / attempts
    denominator = 1 + z * z / attempts
    center = (proportion + z * z / (2 * attempts)) / denominator
    margin = (
        z
        * math.sqrt(
            proportion * (1 - proportion) / attempts
            + z * z / (4 * attempts * attempts)
        )
        / denominator
    )
    return [round(max(0.0, center - margin), 4), round(min(1.0, center + margin), 4)]


def locate_trial(job_dir: Path, selected: dict) -> Path:
    for result_path in sorted(job_dir.glob("*/result.json")):
        try:
            candidate = json.loads(result_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if candidate == selected:
            return result_path.parent
    raise ValueError(f"selected trial is missing under {job_dir}")


def package_artifacts(alias: str, task: str, attempt: int, trial_dir: Path) -> dict:
    destination = PACKAGED / alias / task / f"attempt-{attempt:02d}"
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    sources = {
        "result": (trial_dir / "result.json", "result.json"),
        "trajectory": (trial_dir / "agent" / "trajectory.json", "trajectory.json"),
        "verifier_output": (trial_dir / "verifier" / "output.json", "verifier-output.json"),
    }
    packaged: dict[str, str] = {}
    for label, (source, destination_name) in sources.items():
        artifact = json.loads(source.read_text())
        destination_path = destination / destination_name
        destination_path.write_text(
            json.dumps(redact_artifact(artifact), indent=2) + "\n"
        )
        packaged[label] = str(destination_path.relative_to(ROOT))

    verifier_stdout = trial_dir / "verifier" / "stdout.txt"
    if verifier_stdout.is_file():
        destination_path = destination / "verifier-stdout.txt"
        destination_path.write_text(redact_text(verifier_stdout.read_text()))
        packaged["verifier_stdout"] = str(destination_path.relative_to(ROOT))
    verifier_test_stdout = trial_dir / "verifier" / "test-stdout.txt"
    if verifier_test_stdout.is_file():
        destination_path = destination / "verifier-test-stdout.txt"
        destination_path.write_text(redact_text(verifier_test_stdout.read_text()))
        packaged["verifier_test_stdout"] = str(destination_path.relative_to(ROOT))
    packaged["redaction"] = (
        "Credential assignments, provider tokens, bearer tokens, and private keys redacted."
    )
    return packaged


def collect_attempt(
    alias: str, route: str, task: str, attempt: int, job: str
) -> dict:
    checksum = directory_sha256(ROOT / "tasks" / task)
    job_dir = RAW / job
    result = complete_existing(
        job_dir,
        task,
        route=route,
        snapshot=TASK_SNAPSHOTS[task],
        agent_version=AGENT_VERSION,
        checksum=checksum,
        disable_task_tool=True,
    )
    if result is None:
        raise ValueError(f"missing scoreable current-checksum result: {job}")

    trial_dir = locate_trial(job_dir, result)
    verifier = json.loads((trial_dir / "verifier" / "output.json").read_text())
    trajectory = json.loads((trial_dir / "agent" / "trajectory.json").read_text())
    config = json.loads((ROOT / "tasks" / task / "tests" / "config.json").read_text())
    required = config["fail_to_pass"] + config["pass_to_pass"]
    verdicts = {test["name"]: test["status"] for test in verifier.get("tests", [])}
    failed = [name for name in required if verdicts.get(name) != "passed"]
    reward = result["verifier_result"]["rewards"]["reward"]
    if reward not in (0, 0.0, 1, 1.0):
        raise ValueError(f"non-binary reward in {job}: {reward}")

    agent_execution = result.get("agent_execution") or {}
    agent_result = result.get("agent_result") or {}
    steps = trajectory["steps"]
    return {
        "attempt": attempt,
        "model_alias": alias,
        "task": task,
        "job": job,
        "trial_id": result.get("id"),
        "task_sha256": checksum,
        "started_at": result["started_at"],
        "finished_at": result["finished_at"],
        "reward": int(reward),
        "passed_tests": len(required) - len(failed),
        "total_tests": len(required),
        "failed_tests": failed,
        "model_turns": sum(step.get("source") == "agent" for step in steps),
        "tool_calls": sum(len(step.get("tool_calls") or []) for step in steps),
        "agent_wall_time_seconds": (
            seconds_between(agent_execution["started_at"], agent_execution["finished_at"])
            if agent_execution.get("started_at") and agent_execution.get("finished_at")
            else None
        ),
        "trial_wall_time_seconds": seconds_between(result["started_at"], result["finished_at"]),
        "cost_usd": round(float(agent_result.get("cost_usd") or 0), 6),
        "input_tokens": agent_result.get("n_input_tokens"),
        "cache_tokens": agent_result.get("n_cache_tokens"),
        "output_tokens": agent_result.get("n_output_tokens"),
        "artifacts": package_artifacts(alias, task, attempt, trial_dir),
    }


def effort_summary(attempts: list[dict]) -> dict:
    agent_times = [
        attempt["agent_wall_time_seconds"]
        for attempt in attempts
        if attempt["agent_wall_time_seconds"] is not None
    ]
    trial_times = [attempt["trial_wall_time_seconds"] for attempt in attempts]
    return {
        "model_turns": sum(attempt["model_turns"] for attempt in attempts),
        "tool_calls": sum(attempt["tool_calls"] for attempt in attempts),
        "agent_wall_time_seconds": {
            "mean": round(statistics.mean(agent_times), 3),
            "median": round(statistics.median(agent_times), 3),
            "range": [round(min(agent_times), 3), round(max(agent_times), 3)],
        },
        "trial_wall_time_seconds": {
            "mean": round(statistics.mean(trial_times), 3),
            "median": round(statistics.median(trial_times), 3),
            "range": [round(min(trial_times), 3), round(max(trial_times), 3)],
        },
    }


def task_result(alias: str, spec: dict, task: str) -> dict:
    attempts = [
        collect_attempt(alias, spec["route"], task, number, job)
        for number, job in enumerate(spec["jobs"][task], start=1)
    ]
    if len(attempts) != 8:
        raise ValueError(f"{alias}/{task} has {len(attempts)} attempts instead of eight")
    solves = sum(attempt["reward"] for attempt in attempts)
    failures = Counter(
        failure for attempt in attempts for failure in attempt["failed_tests"]
    )
    best_failure = max(
        (attempt for attempt in attempts if attempt["reward"] == 0),
        key=lambda attempt: (attempt["passed_tests"], -attempt["attempt"]),
        default=None,
    )
    first_win = next(
        (attempt for attempt in attempts if attempt["reward"] == 1), None
    )
    return {
        "task": task,
        **TASK_METADATA[task],
        "task_sha256": attempts[0]["task_sha256"],
        "solves": solves,
        "attempts": len(attempts),
        "solve_rate": round(solves / len(attempts), 4),
        "wilson_95": wilson_interval(solves, len(attempts)),
        "cost_usd": round(sum(attempt["cost_usd"] for attempt in attempts), 6),
        "effort": effort_summary(attempts),
        "recurring_failures": [
            {"test": name, "count": count}
            for name, count in failures.most_common()
        ],
        "best_failed_required_tests": (
            {
                "passed": best_failure["passed_tests"],
                "total": best_failure["total_tests"],
                "attempt": best_failure["attempt"],
            }
            if best_failure
            else None
        ),
        "best_failed_trace": (
            best_failure["artifacts"]["trajectory"] if best_failure else None
        ),
        "first_winning_trace": (
            first_win["artifacts"]["trajectory"] if first_win else None
        ),
        "results": attempts,
    }


def superseded_billing_summary() -> dict:
    jobs = [*SUPERSEDED_BILLING_GROK_JOBS, *SUPERSEDED_BILLING_OPUS_JOBS]
    costs = []
    completed = 0
    for job in jobs:
        path = RAW / job / "result.json"
        if not path.is_file():
            continue
        result = json.loads(path.read_text())
        if result.get("finished_at"):
            completed += 1
        costs.append(float(result.get("stats", {}).get("cost_usd") or 0))
    return {
        "attempts": len(jobs),
        "completed_attempts": completed,
        "cost_usd": round(sum(costs), 6),
        "reason": (
            "Excluded after the billing fairness audit found that one hidden test "
            "graded positional Nest constructor order rather than invoice behavior."
        ),
        "task_sha256": "8855b1ec4ef923e5a3e8e272e89562d34c96a60ba67313195577c5219a4a4ebb",
    }


def main() -> int:
    models = []
    indexed: dict[str, dict[str, dict]] = {}
    for alias, spec in MODEL_SPECS.items():
        task_results = [task_result(alias, spec, task) for task in TASKS]
        indexed[alias] = {item["task"]: item for item in task_results}
        models.append(
            {
                "alias": alias,
                "model": spec["model"],
                "route": spec["route"],
                "agent": f"OpenCode {AGENT_VERSION}",
                "environment": "one isolated Daytona sandbox per attempt",
                "solves": sum(item["solves"] for item in task_results),
                "attempts": sum(item["attempts"] for item in task_results),
                "cost_usd": round(sum(item["cost_usd"] for item in task_results), 6),
                "effort": effort_summary(
                    [attempt for item in task_results for attempt in item["results"]]
                ),
                "tasks": task_results,
            }
        )

    gate = []
    for task in TASKS:
        grok = indexed["grok45"][task]["solves"]
        opus = indexed["opus5"][task]["solves"]
        qualifies = 1 <= grok <= 6 or (grok == 0 and opus > 0)
        if 1 <= grok <= 6:
            reason = "Grok solved between one and six of eight attempts."
        elif grok == 0 and opus > 0:
            reason = "Grok solved zero of eight, while Opus demonstrated learnability."
        elif grok == 0:
            reason = "Neither Grok nor Opus demonstrated learnability in eight attempts."
        else:
            reason = "Grok solved seven or eight attempts, above the requested difficulty band."
        gate.append(
            {
                "task": task,
                "grok45_solves": grok,
                "opus5_solves": opus,
                "qualifies": qualifies,
                "reason": reason,
            }
        )

    every_attempt = [
        attempt
        for model in models
        for task in model["tasks"]
        for attempt in task["results"]
    ]
    first_start = min(parse_timestamp(attempt["started_at"]) for attempt in every_attempt)
    last_finish = max(parse_timestamp(attempt["finished_at"]) for attempt in every_attempt)
    finalization_attempts = [
        attempt
        for attempt in every_attempt
        if attempt["task"] == "paigo-customer-billing-schedule-migration"
        or attempt["attempt"] >= 5
    ]
    finalization_start = min(
        parse_timestamp(attempt["started_at"]) for attempt in finalization_attempts
    )
    finalization_finish = max(
        parse_timestamp(attempt["finished_at"]) for attempt in finalization_attempts
    )
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cohort": "long-horizon enterprise capability-gap study",
        "acceptance_policy": (
            "Eight independent attempts per task and model. Only trials matching the "
            "current task checksum, exact route, OpenCode version, Daytona snapshot, "
            "single-agent policy, and complete verifier output enter the denominator."
        ),
        "binary_win_condition": (
            "Reward 1 requires every configured fail_to_pass and pass_to_pass assertion "
            "to pass; partial repairs receive reward 0."
        ),
        "budget_accounting": {
            "selected_cohort_cost_usd": round(
                sum(attempt["cost_usd"] for attempt in every_attempt), 6
            ),
            "project_recorded_spend_usd": round(recorded_spend(LEDGER), 6),
            "target_budget_usd": 2500,
            "hard_budget_usd": 3000,
            "note": (
                "Recorded spend is conservative and includes exploratory, invalid, "
                "and superseded-checksum trials outside this selected cohort."
            ),
        },
        "cohort_totals": {
            "valid_attempts": len(every_attempt),
            "solves": sum(attempt["reward"] for attempt in every_attempt),
            "cost_usd": round(sum(attempt["cost_usd"] for attempt in every_attempt), 6),
            "model_turns": sum(attempt["model_turns"] for attempt in every_attempt),
            "tool_calls": sum(attempt["tool_calls"] for attempt in every_attempt),
            "first_trial_started_at": first_start.isoformat(),
            "last_trial_finished_at": last_finish.isoformat(),
            "staged_elapsed_window_seconds": round((last_finish - first_start).total_seconds(), 3),
            "note": "The 48-attempt cohort was accumulated in multiple parallel waves.",
        },
        "finalization_batch": {
            "valid_attempts": len(finalization_attempts),
            "solves": sum(attempt["reward"] for attempt in finalization_attempts),
            "cost_usd": round(
                sum(attempt["cost_usd"] for attempt in finalization_attempts), 6
            ),
            "model_turns": sum(
                attempt["model_turns"] for attempt in finalization_attempts
            ),
            "tool_calls": sum(
                attempt["tool_calls"] for attempt in finalization_attempts
            ),
            "started_at": finalization_start.isoformat(),
            "finished_at": finalization_finish.isoformat(),
            "parallel_wall_clock_seconds": round(
                (finalization_finish - finalization_start).total_seconds(), 3
            ),
        },
        "excluded_diagnostics": {
            "superseded_billing_checksum": superseded_billing_summary(),
        },
        "xai_gate": {
            "source": "meeting transcript line 20",
            "rule": (
                "Grok 4.5 solves one to six of eight, or zero of eight when a comparable "
                "model such as Opus 5 completes the task."
            ),
            "qualifying_tasks": sum(item["qualifies"] for item in gate),
            "total_tasks": len(gate),
            "tasks": gate,
        },
        "transcript_alignment": [
            {
                "line": 20,
                "requirement": "eight rollouts and the stated learnability filter",
            },
            {
                "line": 27,
                "requirement": (
                    "win conditions, wall clock, cost, turns, raw traces, and failure modes"
                ),
            },
            {
                "line": 30,
                "requirement": (
                    "general-purpose long-horizon tasks that extend context and reveal "
                    "enterprise evaluation coverage gaps"
                ),
            },
            {
                "line": 34,
                "requirement": (
                    "the more compelling procurement path: an enterprise-derived gap "
                    "where Grok can improve"
                ),
            },
        ],
        "models": models,
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    manifest_paths = [OUTPUT, *sorted(path for path in PACKAGED.rglob("*") if path.is_file())]
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifacts": [
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in manifest_paths
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "gate": f"{output['xai_gate']['qualifying_tasks']}/{len(TASKS)}",
                "models": {
                    model["alias"]: f"{model['solves']}/{model['attempts']}"
                    for model in models
                },
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
