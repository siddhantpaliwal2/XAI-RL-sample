#!/usr/bin/env python3
"""Package Grok 4.5 Daytona jobs and calculate unbiased pass@k scores."""

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
JOB_RE = re.compile(r"^grok45-(.+)-a(\d{2})$")


def pass_at_k(n: int, c: int, k: int) -> float | None:
    if n < k:
        return None
    if n - c < k:
        return 1.0
    return round(1.0 - math.comb(n - c, k) / math.comb(n, k), 4)


def iso_seconds(started: str | None, finished: str | None) -> float | None:
    if not started or not finished:
        return None
    start = datetime.fromisoformat(started.replace("Z", "+00:00"))
    finish = datetime.fromisoformat(finished.replace("Z", "+00:00"))
    return round((finish - start).total_seconds(), 3)


def find_trial_result(job_dir: Path) -> tuple[Path, dict] | None:
    for path in sorted(job_dir.glob("*/result.json")):
        result = json.loads(path.read_text())
        reward = ((result.get("verifier_result") or {}).get("rewards") or {}).get(
            "reward"
        )
        if result.get("exception_info") is None and reward is not None:
            return path.parent, result
    return None


def package_trial(task: str, attempt: int, trial_dir: Path, result: dict) -> dict:
    task_config = json.loads((ROOT / "tasks" / task / "tests" / "config.json").read_text())
    verifier_path = trial_dir / "verifier" / "output.json"
    verifier = json.loads(verifier_path.read_text())
    statuses = {item["name"]: item["status"] for item in verifier["tests"]}
    f2p = task_config["fail_to_pass"]
    p2p = task_config["pass_to_pass"]
    f2p_passed = sum(statuses.get(name) == "passed" for name in f2p)
    p2p_passed = sum(statuses.get(name) == "passed" for name in p2p)

    trajectory_path = trial_dir / "agent" / "trajectory.json"
    trajectory = json.loads(trajectory_path.read_text())
    agent_result = result.get("agent_result") or {}
    reward = float(result["verifier_result"]["rewards"]["reward"])

    packaged = SAMPLE_RUN / "grok-trials" / task / f"attempt-{attempt:02d}"
    packaged.mkdir(parents=True, exist_ok=True)
    copies = {
        trial_dir / "result.json": packaged / "result.json",
        trajectory_path: packaged / "trajectory.json",
        verifier_path: packaged / "verifier-output.json",
        trial_dir / "verifier" / "stdout.txt": packaged / "verifier-stdout.txt",
    }
    for source, destination in copies.items():
        shutil.copy2(source, destination)

    failed_f2p = [name for name in f2p if statuses.get(name) != "passed"]
    failed_p2p = [name for name in p2p if statuses.get(name) != "passed"]
    return {
        "task": task,
        "attempt": attempt,
        "harness": "opencode",
        "model": "x-ai/grok-4.5",
        "provider": "openrouter",
        "reward": reward,
        "f2p_passed": f2p_passed,
        "f2p_total": len(f2p),
        "p2p_passed": p2p_passed,
        "p2p_total": len(p2p),
        "required_passed": f2p_passed + p2p_passed,
        "required_total": len(f2p) + len(p2p),
        "failed_f2p": failed_f2p,
        "failed_p2p": failed_p2p,
        "duration_seconds": iso_seconds(result.get("started_at"), result.get("finished_at")),
        "steps": len(trajectory.get("steps") or []),
        "input_tokens": agent_result.get("n_input_tokens"),
        "cache_tokens": agent_result.get("n_cache_tokens"),
        "output_tokens": agent_result.get("n_output_tokens"),
        "cost_usd": agent_result.get("cost_usd"),
        "trajectory": str((packaged / "trajectory.json").relative_to(SAMPLE_RUN)),
        "result": str((packaged / "result.json").relative_to(SAMPLE_RUN)),
    }


def representative(rows: list[dict]) -> dict:
    return max(
        rows,
        key=lambda row: (
            row["reward"],
            row["f2p_passed"],
            row["p2p_passed"],
            -row["attempt"],
        ),
    )


def markdown_table(task_summaries: list[dict], totals: dict) -> str:
    lines = [
        "# sample-run: Grok 4.5 on the OpenCode harness",
        "",
        "Ten independent attempts per task, run in isolated 2-CPU/4-GB AMD64",
        "Daytona sandboxes. The model route was `openrouter/x-ai/grok-4.5`; every",
        "attempt was graded against the hidden fail-to-pass and pass-to-pass tests.",
        "",
        "## pass@k",
        "",
        "| Task | Solved (c/n) | pass@1 | pass@3 | pass@10 | Avg f2p fixed |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in task_summaries:
        lines.append(
            "| {task} | {c}/{n} | {p1:.3f} | {p3:.3f} | {p10:.3f} | "
            "{avg:.2f}/{f2p_total} |".format(
                task=row["task"],
                c=row["c"],
                n=row["n"],
                p1=row["pass@1"],
                p3=row["pass@3"],
                p10=row["pass@10"],
                avg=row["avg_f2p_passed"],
                f2p_total=row["f2p_total"],
            )
        )
    lines.extend(
        [
            "| **Mean** | **{c}/{n}** | **{p1:.3f}** | **{p3:.3f}** | "
            "**{p10:.3f}** | |".format(
                c=totals["solves"],
                n=totals["attempts"],
                p1=totals["mean_pass@1"],
                p3=totals["mean_pass@3"],
                p10=totals["mean_pass@10"],
            ),
            "",
            "Unbiased pass@k is `1 - C(n-c, k) / C(n, k)`. Means are macro",
            "averages over the eight tasks.",
            "",
            "## Run totals",
            "",
            f"- Valid graded attempts: {totals['attempts']}",
            f"- Full solves: {totals['solves']}",
            f"- Model cost: ${totals['cost_usd']:.2f}",
            f"- Agent runtime: {totals['duration_seconds'] / 60:.1f} minutes (summed)",
            f"- Model steps: {totals['steps']}",
            "",
            "All per-attempt results, verifier verdicts, and trajectories are under",
            "`grok-trials/`. Representative traces (a solve where available, otherwise",
            "the closest graded attempt) are also copied into `trajectories-matrix/`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs-dir", type=Path, default=SAMPLE_RUN / "grok-raw")
    parser.add_argument("--expected-attempts", type=int, default=10)
    args = parser.parse_args()

    rows: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for job_dir in sorted(args.jobs_dir.resolve().glob("grok45-*-a??")):
        match = JOB_RE.match(job_dir.name)
        if not match:
            continue
        task, attempt_text = match.groups()
        attempt = int(attempt_text)
        if task not in TASKS:
            continue
        found = find_trial_result(job_dir)
        if found is None:
            continue
        key = (task, attempt)
        if key in seen:
            raise SystemExit(f"duplicate trial: {task} attempt {attempt}")
        seen.add(key)
        trial_dir, result = found
        rows.append(package_trial(task, attempt, trial_dir, result))

    rows.sort(key=lambda row: (TASKS.index(row["task"]), row["attempt"]))
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["task"]].append(row)

    missing = {
        task: args.expected_attempts - len(grouped[task])
        for task in TASKS
        if len(grouped[task]) != args.expected_attempts
    }
    if missing:
        raise SystemExit(f"incomplete matrix: {missing}")

    task_summaries: list[dict] = []
    matrix_path = SAMPLE_RUN / "passk_matrix.json"
    matrix = json.loads(matrix_path.read_text())
    for task in TASKS:
        task_rows = grouped[task]
        n = len(task_rows)
        c = sum(row["reward"] >= 1.0 for row in task_rows)
        summary = {
            "task": task,
            "n": n,
            "c": c,
            "pass@1": pass_at_k(n, c, 1),
            "pass@3": pass_at_k(n, c, 3),
            "pass@10": pass_at_k(n, c, 10),
            "avg_f2p_passed": round(sum(row["f2p_passed"] for row in task_rows) / n, 3),
            "f2p_total": task_rows[0]["f2p_total"],
            "avg_p2p_passed": round(sum(row["p2p_passed"] for row in task_rows) / n, 3),
            "p2p_total": task_rows[0]["p2p_total"],
        }
        task_summaries.append(summary)
        matrix[f"opencode|grok-4.5|{task}"] = {
            "n": n,
            "c": c,
            "pass@1": summary["pass@1"],
            "pass@10": summary["pass@10"],
            "pass@3": summary["pass@3"],
        }

        best = representative(task_rows)
        source = SAMPLE_RUN / best["trajectory"]
        suffix = "--SOLVED" if best["reward"] >= 1 else ""
        matrix_target = (
            SAMPLE_RUN
            / "trajectories-matrix"
            / f"{task}--opencode--grok-4.5{suffix}.trajectory.json"
        )
        shutil.copy2(source, matrix_target)
        comparison_target = SAMPLE_RUN / "trajectories" / f"{task}--grok-4.5.trajectory.json"
        shutil.copy2(source, comparison_target)

    totals = {
        "attempts": len(rows),
        "solves": sum(row["reward"] >= 1 for row in rows),
        "mean_pass@1": round(sum(row["pass@1"] for row in task_summaries) / len(TASKS), 4),
        "mean_pass@3": round(sum(row["pass@3"] for row in task_summaries) / len(TASKS), 4),
        "mean_pass@10": round(sum(row["pass@10"] for row in task_summaries) / len(TASKS), 4),
        "cost_usd": round(sum((row["cost_usd"] or 0) for row in rows), 4),
        "duration_seconds": round(sum((row["duration_seconds"] or 0) for row in rows), 3),
        "steps": sum(row["steps"] for row in rows),
    }

    (SAMPLE_RUN / "grok_trials.json").write_text(json.dumps(rows, indent=2) + "\n")
    (SAMPLE_RUN / "results.json").write_text(
        json.dumps(
            {
                "model": "openrouter/x-ai/grok-4.5",
                "harness": "opencode",
                "environment": "daytona-2cpu-4gb-amd64",
                "attempts_per_task": args.expected_attempts,
                "tasks": task_summaries,
                "totals": totals,
                "per_attempt_data": "grok_trials.json",
            },
            indent=2,
        )
        + "\n"
    )
    matrix_path.write_text(json.dumps(matrix, indent=1) + "\n")
    (SAMPLE_RUN / "results.md").write_text(markdown_table(task_summaries, totals))
    print(json.dumps({"tasks": task_summaries, "totals": totals}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
