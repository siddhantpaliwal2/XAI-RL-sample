#!/usr/bin/env python3
"""Recover a completed OpenCode trial from a stalled Daytona collector.

Use only after the remote OpenCode process has exited. The script captures the
agent patch before injecting the original hidden verifier, runs that verifier
in the existing sandbox, downloads the evidence, reconstructs the ATIF
trajectory from OpenCode's JSON stream, and writes a standard Harbor-compatible
result. It deliberately does not terminate the Harbor process or sandbox; the
operator does that only after verifying the recovered files.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from daytona import Daytona, DaytonaConfig
from harbor.agents.installed.opencode import OpenCode
from harbor.utils.trajectory_utils import format_trajectory_json

from run_frontier_daytona import TASK_SNAPSHOTS, directory_sha256


ROOT = Path(__file__).resolve().parent.parent


def iso_from_millis(value: int | float) -> str:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sandbox-id", required=True)
    parser.add_argument("--job-dir", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--route", required=True)
    parser.add_argument("--agent-version", default="1.18.13")
    args = parser.parse_args()

    api_key = os.environ.get("DAYTONA_API_KEY")
    if not api_key:
        raise SystemExit("DAYTONA_API_KEY is required")
    api_url = os.environ.get("DAYTONA_API_URL", "https://app.daytona.io/api")
    client = Daytona(DaytonaConfig(api_key=api_key, api_url=api_url))
    sandbox = client.get(args.sandbox_id)

    job_dir = args.job_dir.expanduser().resolve()
    task_dir = ROOT / "tasks" / args.task
    tests_dir = task_dir / "tests"
    if not task_dir.is_dir() or not tests_dir.is_dir():
        raise SystemExit(f"unknown task: {args.task}")
    job_dir.mkdir(parents=True, exist_ok=True)
    trial_dirs = [path for path in job_dir.iterdir() if path.is_dir()]
    if not trial_dirs:
        trial_name = f"{args.task}__recovered_{args.sandbox_id[:8]}"
        trial_dir = job_dir / trial_name
        trial_dir.mkdir()
        trial_config = {
            "task": {"path": f"tasks/{args.task}"},
            "trial_name": trial_name,
            "trials_dir": str(job_dir),
            "agent": {
                "name": "opencode",
                "model_name": args.route,
                "kwargs": {"version": args.agent_version},
            },
            "environment": {
                "type": "daytona",
                "kwargs": {
                    "snapshot_template_name": TASK_SNAPSHOTS[args.task],
                    "assume_global_snapshot": True,
                },
            },
            "job_id": str(uuid4()),
        }
        (trial_dir / "config.json").write_text(
            json.dumps(trial_config, indent=2) + "\n"
        )
    elif len(trial_dirs) == 1:
        trial_dir = trial_dirs[0]
    else:
        raise SystemExit(f"expected at most one trial directory under {job_dir}")
    trial_config_path = trial_dir / "config.json"
    if not trial_config_path.is_file():
        raise SystemExit(f"missing trial config: {trial_config_path}")

    # Refuse to grade while an agent is still running.
    running = sandbox.process.exec(
        "count=0; for p in /proc/[0-9]*; do "
        "c=$(tr '\\0' ' ' < \"$p/cmdline\" 2>/dev/null || true); "
        "case \"$c\" in *opencode*--model=*) count=$((count+1));; esac; "
        "done; echo $count",
        timeout=30,
    )
    if running.result.strip() != "0":
        raise SystemExit(f"OpenCode is still running in {args.sandbox_id}")

    sandbox.process.exec(
        "mkdir -p /logs/agent /logs/artifacts /logs/verifier /tests && "
        "test -s /logs/artifacts/agent.patch || "
        "(cd /app && git add -N . && git diff --binary > /logs/artifacts/agent.patch)",
        timeout=120,
    )
    for source in sorted(tests_dir.iterdir()):
        if source.is_file():
            sandbox.fs.upload_file(str(source), f"/tests/{source.name}")
    sandbox.process.exec("chmod +x /tests/test.sh /tests/run_script.sh", timeout=30)

    verifier_started = datetime.now(timezone.utc)
    verifier_run = sandbox.process.exec(
        "REWARD_DIR=/logs/verifier sh /tests/test.sh", timeout=1800
    )
    verifier_finished = datetime.now(timezone.utc)
    if verifier_run.exit_code != 0:
        raise SystemExit(f"verifier command exited {verifier_run.exit_code}")

    agent_dir = trial_dir / "agent"
    verifier_dir = trial_dir / "verifier"
    artifacts_dir = trial_dir / "artifacts"
    agent_dir.mkdir(parents=True, exist_ok=True)
    verifier_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    downloads = {
        "/logs/agent/opencode.txt": agent_dir / "opencode.txt",
        "/logs/artifacts/agent.patch": artifacts_dir / "agent.patch",
        "/logs/verifier/output.json": verifier_dir / "output.json",
        "/logs/verifier/stdout.txt": verifier_dir / "stdout.txt",
        "/logs/verifier/reward.txt": verifier_dir / "reward.txt",
    }
    for remote, local in downloads.items():
        sandbox.fs.download_file(remote, str(local))

    verifier = json.loads((verifier_dir / "output.json").read_text())
    if not verifier.get("tests"):
        raise SystemExit("recovered verifier output has no test verdicts")
    reward_text = (verifier_dir / "reward.txt").read_text().strip()
    if reward_text not in {"0", "1"}:
        raise SystemExit(f"invalid reward: {reward_text}")
    reward = float(reward_text)

    instruction = (task_dir / "instruction.md").read_text()
    agent = OpenCode(
        logs_dir=agent_dir,
        version=args.agent_version,
        model_name=args.route,
    )
    agent._instruction = instruction  # Reconstruct the omitted OpenCode user event.
    events = agent._parse_stdout()
    trajectory = agent._convert_events_to_trajectory(events)
    if trajectory is None or not trajectory.steps:
        raise SystemExit("could not reconstruct trajectory")
    (agent_dir / "trajectory.json").write_text(
        format_trajectory_json(trajectory.to_json_dict())
    )

    timestamps = [
        event.get("timestamp")
        for event in events
        if isinstance(event.get("timestamp"), (int, float))
    ]
    if not timestamps:
        raise SystemExit("OpenCode stream has no timestamps")
    agent_started_at = iso_from_millis(min(timestamps))
    agent_finished = datetime.fromtimestamp(max(timestamps) / 1000, tz=timezone.utc)
    verifier_duration = verifier_finished - verifier_started
    synthetic_finished = agent_finished + verifier_duration
    sandbox_created = datetime.fromisoformat(
        sandbox.created_at.replace("Z", "+00:00")
    )
    if synthetic_finished <= sandbox_created:
        raise SystemExit("invalid recovered timestamp ordering")

    trial_config = json.loads(trial_config_path.read_text())
    route = trial_config.get("agent", {}).get("model_name")
    if route != args.route:
        raise SystemExit(f"trial route mismatch: {route}")
    provider, model_name = args.route.split("/", 1)
    final_metrics = trajectory.final_metrics
    result = {
        "id": str(uuid4()),
        "task_name": args.task,
        "trial_name": trial_dir.name,
        "trial_uri": trial_dir.as_uri(),
        "task_id": {"path": f"tasks/{args.task}"},
        "source": None,
        "task_checksum": directory_sha256(task_dir),
        "config": trial_config,
        "agent_info": {
            "name": "opencode",
            "version": args.agent_version,
            "model_info": {"name": model_name, "provider": provider},
        },
        "agent_result": {
            "n_input_tokens": final_metrics.total_prompt_tokens or 0,
            "n_cache_tokens": final_metrics.total_cached_tokens or 0,
            "n_output_tokens": final_metrics.total_completion_tokens or 0,
            "cost_usd": final_metrics.total_cost_usd,
            "rollout_details": None,
            "metadata": {
                "recovered_from_stalled_daytona_collector": True,
            },
        },
        "verifier_result": {"rewards": {"reward": reward}},
        "exception_info": None,
        "started_at": sandbox_created.isoformat().replace("+00:00", "Z"),
        "finished_at": synthetic_finished.isoformat().replace("+00:00", "Z"),
        "environment_setup": None,
        "agent_setup": None,
        "agent_execution": {
            "started_at": agent_started_at,
            "finished_at": agent_finished.isoformat().replace("+00:00", "Z"),
        },
        "verifier": {
            "started_at": verifier_started.isoformat().replace("+00:00", "Z"),
            "finished_at": verifier_finished.isoformat().replace("+00:00", "Z"),
        },
        "step_results": None,
        "recovery": {
            "reason": "daytona_process_exec_collection_stall",
            "sandbox_id": args.sandbox_id,
            "duration_basis": "sandbox_created_to_agent_finish_plus_manual_verifier_runtime",
            "manual_verifier_wall_time_seconds": round(
                verifier_duration.total_seconds(), 3
            ),
            "recovered_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
        },
    }
    (trial_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    metadata = {
        "model_route": args.route,
        "snapshot": TASK_SNAPSHOTS[args.task],
        "agent_version": args.agent_version,
        "task_sha256": directory_sha256(task_dir),
    }
    (job_dir / "matrix-metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "trial_dir": str(trial_dir),
                "reward": reward,
                "trajectory_steps": len(trajectory.steps),
                "verifier_tests": len(verifier["tests"]),
                "agent_patch_bytes": (artifacts_dir / "agent.patch").stat().st_size,
                "manual_verifier_seconds": round(verifier_duration.total_seconds(), 3),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
