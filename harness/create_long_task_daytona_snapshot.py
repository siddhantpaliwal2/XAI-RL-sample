#!/usr/bin/env python3
"""Build the long-horizon task's sealed Daytona snapshot from a pinned checkout."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from daytona import CreateSnapshotParams, Daytona, Image, Resources


BASE_COMMIT = "a03ff50b9e6868565ba88be5f7438f4ac7583138"
SNAPSHOT = "harbor-probe-long-native-table-migration-4g"


def load_env(path: Path) -> None:
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key] = value.strip().strip('"').strip("'")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.expanduser().resolve()
    env_file = args.env_file.expanduser().resolve()
    if not (repo / "pom.xml").is_file():
        parser.error(f"not a bank-statement-parser checkout: {repo}")
    if not env_file.is_file():
        parser.error(f"env file does not exist: {env_file}")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if commit != BASE_COMMIT:
        parser.error(f"checkout must be pinned to {BASE_COMMIT}; found {commit}")

    load_env(env_file)
    client = Daytona()
    existing = [item for item in client.snapshot.list(limit=100).items if item.name == SNAPSHOT]
    if existing:
        parser.error(f"snapshot already exists: {SNAPSHOT} ({existing[0].state})")

    image = (
        Image.base("maven:3.9-eclipse-temurin-17")
        .run_commands(
            "apt-get update && apt-get install -y --no-install-recommends git python3 curl && rm -rf /var/lib/apt/lists/*"
        )
        .add_local_dir(repo, "/app")
        .workdir("/app")
        .run_commands(
            "rm -rf .git src/test/java",
            "mvn -B -q -DskipTests dependency:go-offline || true",
            "mvn -B -q dependency:get -Dartifact=org.json:json:20240303 && "
            "mvn -B -q dependency:get -Dartifact=commons-io:commons-io:2.21.0",
            "mvn -B -q -DskipTests package",
            "mkdir -p src/test/java/com/finboost/bank/statement/parser && "
            "printf '%s\\n' 'package com.finboost.bank.statement.parser;' "
            "'import org.junit.jupiter.api.Test;' "
            "'import static org.junit.jupiter.api.Assertions.assertEquals;' "
            "'class WarmProviderTest { @Test void ok(){ assertEquals(2, 1 + 1); } }' "
            "> src/test/java/com/finboost/bank/statement/parser/WarmProviderTest.java && "
            "mvn -B -q -Dtest=WarmProviderTest test && "
            "rm -rf src/test/java target/test-classes target/surefire-reports",
            "git init -qb main && git config user.email t@t && git config user.name t && "
            "git add -A && git commit -qm 'import codebase'",
            "mkdir -p /logs/verifier",
        )
    )
    snapshot = client.snapshot.create(
        CreateSnapshotParams(
            name=SNAPSHOT,
            image=image,
            resources=Resources(cpu=2, memory=4, disk=10),
        ),
        on_logs=lambda chunk: print(chunk, flush=True),
        timeout=0,
    )
    print(f"snapshot={snapshot.name} state={snapshot.state}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
