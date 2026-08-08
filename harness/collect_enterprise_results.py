#!/usr/bin/env python3
"""Collect only final-checksum enterprise calibration attempts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from run_enterprise_daytona import TASK_SNAPSHOTS, complete_existing
from run_frontier_daytona import directory_sha256


ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "sample-run" / "enterprise-raw"
OUTPUT = ROOT / "sample-run" / "enterprise-model-results.json"
ROUTE = "amazon-bedrock/global.anthropic.claude-opus-5"
AGENT_VERSION = "1.18.13"
OPUS_JOBS = {
    "paigo-dimension-pricing-tiers": (
        "enterprise-opus-isolated-tests-r1-opus5-bedrock-"
        "paigo-dimension-pricing-tiers-a01"
    ),
    "paigo-top-up-billing-lifecycle": (
        "enterprise-opus-isolated-tests-r1-opus5-bedrock-"
        "paigo-top-up-billing-lifecycle-a01"
    ),
    "paigo-s3-datastore-measurement": (
        "enterprise-opus-reserved-tests-r1-opus5-bedrock-"
        "paigo-s3-datastore-measurement-a01"
    ),
    "paigo-customer-identity-migration": (
        "enterprise-opus-reserved-tests-r1-opus5-bedrock-"
        "paigo-customer-identity-migration-a01"
    ),
    "paigo-customer-billing-schedule-migration": (
        "enterprise-opus-regrade-r1-opus5-bedrock-"
        "paigo-customer-billing-schedule-migration-a01"
    ),
    "champ-email-inbox-infrastructure": (
        "enterprise-opus-reserved-tests-r1-opus5-bedrock-"
        "champ-email-inbox-infrastructure-a01"
    ),
    "finbit-bank-parser-consolidation": (
        "enterprise-opus-stage1-r1-opus5-bedrock-"
        "finbit-bank-parser-consolidation-a01"
    ),
    "finbit-google-cloud-storage-migration": (
        "enterprise-opus-cloud-fair-r1-opus5-bedrock-"
        "finbit-google-cloud-storage-migration-a01"
    ),
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
    agent_result = result["agent_result"]
    reward = result["verifier_result"]["rewards"]["reward"]
    started = parse_timestamp(result["started_at"])
    finished = parse_timestamp(result["finished_at"])
    steps = trajectory["steps"]
    failed = [item["name"] for item in tests if item["status"] != "passed"]
    return {
        "task": task,
        "job": job,
        "task_sha256": checksum,
        "reward": reward,
        "passed_tests": len(tests) - len(failed),
        "total_tests": len(tests),
        "failed_tests": failed,
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
    attempts = [collect_attempt(task, job) for task, job in OPUS_JOBS.items()]
    opus_passes = sum(item["reward"] == 1 for item in attempts)
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "acceptance_policy": (
            "Only complete trials matching the final task checksum, exact model route, "
            "OpenCode version, Daytona snapshot, and denied task tool are counted."
        ),
        "models": [
            {
                "model": "Claude Opus 5",
                "route": ROUTE,
                "status": "initial-stage-complete",
                "solves": opus_passes,
                "attempts": len(attempts),
                "cost_usd": round(sum(item["cost_usd"] for item in attempts), 6),
                "results": attempts,
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
                    "Zero-turn transport probes are excluded."
                ),
            },
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"output": str(OUTPUT), "opus": f"{opus_passes}/8"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
