#!/usr/bin/env python3
"""Summarize fresh Harbor result directories with the report's pass@k schema."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path


def model_label(route: str) -> str:
    if "grok-4.5" in route:
        return "Grok 4.5"
    if "claude-opus-5" in route:
        return "Claude Opus 5"
    return route


def pass_at_k(n: int, c: int, k: int) -> float | None:
    if k > n:
        return None
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def load_results(roots: list[Path]) -> dict[tuple[str, str], list[int]]:
    grouped: dict[tuple[str, str], list[int]] = defaultdict(list)
    seen_trials: set[str] = set()
    for root in roots:
        for result_path in sorted(root.rglob("result.json")):
            try:
                result = json.loads(result_path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            reward = (
                ((result.get("verifier_result") or {}).get("rewards") or {}).get(
                    "reward"
                )
            )
            if result.get("exception_info") is not None or reward not in {0, 0.0, 1, 1.0}:
                continue
            trial_id = str(result.get("id") or result_path.resolve())
            if trial_id in seen_trials:
                continue
            seen_trials.add(trial_id)
            task = result.get("task_name")
            route = ((result.get("config") or {}).get("agent") or {}).get(
                "model_name"
            )
            if not task or not route:
                continue
            grouped[(model_label(route), task)].append(int(reward))
    return grouped


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("result_dirs", nargs="+", type=Path)
    parser.add_argument("--expected-attempts", type=int)
    parser.add_argument(
        "--k",
        default="1,3,8",
        help="comma-separated pass@k values (default: 1,3,8)",
    )
    args = parser.parse_args()

    try:
        k_values = [int(value) for value in args.k.split(",")]
    except ValueError:
        parser.error("--k must be a comma-separated list of integers")

    roots = [path.expanduser().resolve() for path in args.result_dirs]
    missing = [str(path) for path in roots if not path.is_dir()]
    if missing:
        parser.error(f"result directories do not exist: {', '.join(missing)}")
    if not k_values or any(k < 1 for k in k_values):
        parser.error("all k values must be positive")

    grouped = load_results(roots)
    if not grouped:
        parser.error("no complete verifier results found")

    bad_counts = []
    if args.expected_attempts is not None:
        bad_counts = [
            (model, task, len(rewards))
            for (model, task), rewards in grouped.items()
            if len(rewards) != args.expected_attempts
        ]

    columns = ["Model", "Task", "Solves (c/n)"] + [
        f"pass@{k}" for k in k_values
    ]
    print("| " + " | ".join(columns) + " |")
    print("|" + "|".join("---" for _ in columns) + "|")

    macro: dict[str, list[tuple[int, int, list[float | None]]]] = defaultdict(list)
    for (model, task), rewards in sorted(grouped.items()):
        n = len(rewards)
        c = sum(rewards)
        values = [pass_at_k(n, c, k) for k in k_values]
        cells = [model, task, f"{c}/{n}"] + [
            "N/A" if value is None else f"{value:.4f}" for value in values
        ]
        print("| " + " | ".join(cells) + " |")
        macro[model].append((c, n, values))

    for model, rows in sorted(macro.items()):
        solves = sum(row[0] for row in rows)
        attempts = sum(row[1] for row in rows)
        means = []
        for index in range(len(k_values)):
            measured = [row[2][index] for row in rows if row[2][index] is not None]
            means.append(sum(measured) / len(measured) if measured else None)
        cells = [model, "Macro mean", f"{solves}/{attempts}"] + [
            "N/A" if value is None else f"{value:.4f}" for value in means
        ]
        print("| **" + "** | **".join(cells) + "** |")

    if bad_counts:
        print("\nIncomplete cells:")
        for model, task, count in sorted(bad_counts):
            print(
                f"  {model} / {task}: {count}, expected {args.expected_attempts}"
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
