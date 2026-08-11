#!/usr/bin/env python3
"""Run the Grok 4.5 OpenCode pass@k matrix on Daytona.

Each of the eight tasks receives ten independent attempts.  The global worker
pool bounds Daytona concurrency across tasks, avoiding the capacity failures
caused by launching all 80 sandboxes at once.  Completed, fully graded trials
are reused on restart; infrastructure failures are retried.

Usage:
    python harness/run_grok_daytona.py \
      --env-file /absolute/path/to/daytona-openrouter.env \
      --concurrency 12
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MODEL = "openrouter/x-ai/grok-4.5"
TASK_SNAPSHOTS = {
    "latent-credit-normalize": "harbor-probe-latent-credit-normalize-4g",
    "latent-doc-extractors": "harbor-probe-latent-doc-extractors-4g",
    "latent-financial-tools": "harbor-probe-latent-financial-tools-4g",
    "latent-phone-invites": "harbor-probe-latent-phone-invites-4g",
    "xrepo-fiu-latent": "harbor-probe-xrepo-fiu-latent-4g",
    "xrepo-txenrich-latent": "harbor-probe-xrepo-txenrich-latent-4g",
    "xrepo-txenrich3-latent": "harbor-probe-xrepo-txenrich3-latent-4g",
    "xrepo-txenrich4-latent": "harbor-probe-xrepo-txenrich4-latent-4g",
}
PRINT_LOCK = threading.Lock()


def trial_result(job_dir: Path) -> dict | None:
    """Return a valid graded trial result, or None for an incomplete job."""
    for path in job_dir.glob("*__/result.json"):
        try:
            result = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        reward = ((result.get("verifier_result") or {}).get("rewards") or {}).get(
            "reward"
        )
        if result.get("exception_info") is None and reward is not None:
            return result
    # Harbor trial directories use a random suffix after a double underscore.
    for path in job_dir.glob("*/result.json"):
        try:
            result = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        reward = ((result.get("verifier_result") or {}).get("rewards") or {}).get(
            "reward"
        )
        if result.get("exception_info") is None and reward is not None:
            return result
    return None


def emit(message: str) -> None:
    with PRINT_LOCK:
        print(message, flush=True)


def run_one(
    task: str,
    attempt: int,
    *,
    env_file: Path,
    jobs_dir: Path,
    logs_dir: Path,
    retries: int,
) -> dict:
    job_name = f"grok45-{task}-a{attempt:02d}"
    job_dir = jobs_dir / job_name
    existing = trial_result(job_dir)
    if existing is not None:
        reward = existing["verifier_result"]["rewards"]["reward"]
        emit(f"REUSE {job_name} reward={reward}")
        return {"job": job_name, "status": "reused", "reward": reward}

    command = [
        "harbor",
        "run",
        "-p",
        f"tasks/{task}",
        "-e",
        "daytona",
        "--ek",
        f"snapshot_template_name={TASK_SNAPSHOTS[task]}",
        "--ek",
        "assume_global_snapshot=true",
        "-a",
        "opencode",
        "-m",
        MODEL,
        "--env-file",
        str(env_file),
        "-k",
        "1",
        "-n",
        "1",
        "-o",
        str(jobs_dir),
        "--job-name",
        job_name,
        "-q",
        "-y",
    ]

    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{job_name}.log"
    for retry in range(retries + 1):
        if job_dir.exists():
            shutil.rmtree(job_dir)
        emit(f"START {job_name} try={retry + 1}")
        with log_path.open("a") as log:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=3600,
                check=False,
            )
        result = trial_result(job_dir)
        if result is not None:
            reward = result["verifier_result"]["rewards"]["reward"]
            emit(f"DONE  {job_name} reward={reward}")
            return {
                "job": job_name,
                "status": "completed",
                "reward": reward,
                "returncode": completed.returncode,
            }
        emit(f"RETRY {job_name} returncode={completed.returncode}")

    emit(f"FAILED {job_name}")
    return {"job": job_name, "status": "failed", "reward": None}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--concurrency", type=int, default=12)
    parser.add_argument("--attempts", type=int, default=10)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument(
        "--jobs-dir", type=Path, default=ROOT / "sample-run" / "grok-raw"
    )
    args = parser.parse_args()

    env_file = args.env_file.expanduser().resolve()
    if not env_file.is_file():
        parser.error(f"env file does not exist: {env_file}")
    if args.concurrency < 1 or args.attempts < 1 or args.retries < 0:
        parser.error("concurrency and attempts must be positive; retries cannot be negative")

    jobs_dir = args.jobs_dir.resolve()
    logs_dir = ROOT / "sample-run" / "runner-logs"
    jobs = [
        (task, attempt)
        for task in TASK_SNAPSHOTS
        for attempt in range(1, args.attempts + 1)
    ]
    emit(
        f"Grok 4.5 matrix: {len(jobs)} trials, "
        f"Daytona concurrency={args.concurrency}"
    )

    outcomes: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {
            pool.submit(
                run_one,
                task,
                attempt,
                env_file=env_file,
                jobs_dir=jobs_dir,
                logs_dir=logs_dir,
                retries=args.retries,
            ): (task, attempt)
            for task, attempt in jobs
        }
        for future in as_completed(futures):
            task, attempt = futures[future]
            try:
                outcomes.append(future.result())
            except Exception as exc:  # noqa: BLE001
                emit(f"ERROR grok45-{task}-a{attempt:02d} {type(exc).__name__}: {exc}")
                outcomes.append(
                    {
                        "job": f"grok45-{task}-a{attempt:02d}",
                        "status": "failed",
                        "reward": None,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

    outcomes.sort(key=lambda item: item["job"])
    summary_path = ROOT / "sample-run" / "run-summaries" / "grok-run-summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(outcomes, indent=2) + "\n")
    failures = [item for item in outcomes if item["reward"] is None]
    emit(f"SUMMARY valid={len(outcomes) - len(failures)} failed={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
