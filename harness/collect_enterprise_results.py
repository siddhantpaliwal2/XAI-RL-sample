#!/usr/bin/env python3
"""Collect only final-checksum enterprise calibration attempts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from run_enterprise_daytona import TASK_SNAPSHOTS, complete_existing, recorded_spend
from run_frontier_daytona import directory_sha256


ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "sample-run" / "enterprise-raw"
LEDGER = ROOT / "sample-run" / "enterprise-budget-ledger.jsonl"
OUTPUT = ROOT / "sample-run" / "enterprise-model-results.json"
ROUTE = "amazon-bedrock/global.anthropic.claude-opus-5"
AGENT_VERSION = "1.18.13"
OPUS_A01 = {
    "paigo-dimension-pricing-tiers": (
        "enterprise-opus-pricing-final-r1-opus5-bedrock-"
        "paigo-dimension-pricing-tiers-a01"
    ),
    "paigo-top-up-billing-lifecycle": (
        "enterprise-opus-final-a01-r1-opus5-bedrock-"
        "paigo-top-up-billing-lifecycle-a01"
    ),
    "paigo-s3-datastore-measurement": (
        "enterprise-opus-final-a01-r1-opus5-bedrock-"
        "paigo-s3-datastore-measurement-a01"
    ),
    "paigo-customer-identity-migration": (
        "enterprise-opus-reserved-tests-r1-opus5-bedrock-"
        "paigo-customer-identity-migration-a01"
    ),
    "paigo-customer-billing-schedule-migration": (
        "enterprise-opus-final-taxonomy-r1-opus5-bedrock-"
        "paigo-customer-billing-schedule-migration-a01"
    ),
    "champ-email-inbox-infrastructure": (
        "enterprise-opus-fair-complete-r1-opus5-bedrock-"
        "champ-email-inbox-infrastructure-a01"
    ),
    "finbit-bank-parser-consolidation": (
        "enterprise-opus-final-a01-r1-opus5-bedrock-"
        "finbit-bank-parser-consolidation-a01"
    ),
    "finbit-google-cloud-storage-migration": (
        "enterprise-opus-cloud-fair-r1-opus5-bedrock-"
        "finbit-google-cloud-storage-migration-a01"
    ),
}
OPUS_JOBS = {
    task: [
        first_job,
        *[
            (
                f"enterprise-opus-pricing-final-r1-opus5-bedrock-{task}-a{attempt:02d}"
                if task == "paigo-dimension-pricing-tiers"
                else f"enterprise-opus-final-a23-r1-opus5-bedrock-{task}-a{attempt:02d}"
            )
            for attempt in (2, 3)
        ],
    ]
    for task, first_job in OPUS_A01.items()
}


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def trial_dir_for_result(job_dir: Path, result: dict) -> Path:
    for result_path in sorted(job_dir.glob("*/result.json")):
        try:
            candidate = json.loads(result_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if candidate == result:
            return result_path.parent
    raise ValueError(f"could not locate selected result under {job_dir}")


def collect_attempt(task: str, job: str) -> dict:
    job_dir = RAW / job
    checksum = directory_sha256(ROOT / "tasks" / task)
    result = complete_existing(
        job_dir,
        task,
        route=ROUTE,
        snapshot=TASK_SNAPSHOTS[task],
        agent_version=AGENT_VERSION,
        checksum=checksum,
        disable_task_tool=True,
    )
    if result is None:
        raise ValueError(f"missing final-checksum result: {job}")
    trial_dir = trial_dir_for_result(job_dir, result)
    trajectory = json.loads((trial_dir / "agent" / "trajectory.json").read_text())
    verifier = json.loads((trial_dir / "verifier" / "output.json").read_text())
    tests = verifier["tests"]
    config = json.loads((ROOT / "tasks" / task / "tests" / "config.json").read_text())
    required = config["fail_to_pass"] + config["pass_to_pass"]
    verdicts = {item["name"]: item["status"] for item in tests}
    agent_result = result["agent_result"]
    reward = result["verifier_result"]["rewards"]["reward"]
    started = parse_timestamp(result["started_at"])
    finished = parse_timestamp(result["finished_at"])
    steps = trajectory["steps"]
    failed = [name for name in required if verdicts[name] != "passed"]
    auxiliary_failed = [
        item["name"]
        for item in tests
        if item["name"] not in required and item["status"] != "passed"
    ]
    return {
        "task": task,
        "job": job,
        "task_sha256": checksum,
        "reward": reward,
        "passed_tests": len(required) - len(failed),
        "total_tests": len(required),
        "failed_tests": failed,
        "auxiliary_failed_tests": auxiliary_failed,
        "model_turns": sum(step.get("source") == "agent" for step in steps),
        "tool_calls": sum(len(step.get("tool_calls") or []) for step in steps),
        "wall_time_seconds": round((finished - started).total_seconds(), 3),
        "cost_usd": float(agent_result.get("cost_usd") or 0),
        "input_tokens": agent_result.get("n_input_tokens"),
        "cache_tokens": agent_result.get("n_cache_tokens"),
        "output_tokens": agent_result.get("n_output_tokens"),
        "grading_provenance": "final task checksum; complete verifier output",
    }


def main() -> int:
    attempts = [
        collect_attempt(task, job)
        for task, jobs in OPUS_JOBS.items()
        for job in jobs
    ]
    opus_passes = sum(item["reward"] == 1 for item in attempts)
    opus_cost = round(sum(item["cost_usd"] for item in attempts), 6)
    task_results = []
    for task in OPUS_JOBS:
        task_attempts = [item for item in attempts if item["task"] == task]
        solves = sum(item["reward"] == 1 for item in task_attempts)
        task_results.append(
            {
                "task": task,
                "solves": solves,
                "attempts": len(task_attempts),
                "pass_at_1": round(solves / len(task_attempts), 6),
                "results": task_attempts,
            }
        )
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "acceptance_policy": (
            "Only complete trials matching the final task checksum, exact model route, "
            "OpenCode version, Daytona snapshot, and denied task tool are counted."
        ),
        "budget_accounting": {
            "selected_trial_cost_usd": opus_cost,
            "recorded_spend_usd": round(recorded_spend(LEDGER), 6),
            "target_budget_usd": 2000,
            "hard_budget_usd": 3000,
            "note": (
                "Recorded spend is conservative and includes exploratory and "
                "superseded-checksum trials excluded from the score denominator."
            ),
        },
        "models": [
            {
                "model": "Claude Opus 5",
                "route": ROUTE,
                "status": "three-attempt-stage-complete",
                "solves": opus_passes,
                "attempts": len(attempts),
                "macro_pass_at_1": round(
                    sum(item["pass_at_1"] for item in task_results)
                    / len(task_results),
                    6,
                ),
                "cost_usd": opus_cost,
                "task_results": task_results,
            },
            {
                "model": "Grok 4.5",
                "status": "blocked-no-exact-provider-credential",
                "scored_attempts": 0,
                "note": (
                    "Amazon Bedrock does not expose Grok 4.5. An OpenRouter or xAI "
                    "credential is required; no substitute Grok version is counted."
                ),
            },
            {
                "model": "GPT-5.6 Sol",
                "status": "blocked-daytona-network-tier",
                "scored_attempts": 0,
                "note": (
                    "The exact Bedrock Mantle model works from the host, but Daytona "
                    "resets both direct Mantle and authenticated relay connections. "
                    "An exact OpenRouter route would avoid that network path; zero-turn "
                    "transport probes are excluded."
                ),
            },
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {"output": str(OUTPUT), "opus": f"{opus_passes}/{len(attempts)}"}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
