#!/usr/bin/env python3
"""Regenerate the long native-table task's hidden-test config and read-only copies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TASK = ROOT / "tasks" / "long-native-table-migration"
TEST_DESTINATION = (
    "src/test/java/com/finboost/bank/statement/parser/longhorizon/"
    "NativeTableMigrationTest.java"
)


def added_file_patch(source: str) -> str:
    lines = source.splitlines()
    body = "\n".join(f"+{line}" for line in lines) + "\n"
    return (
        f"diff --git a/{TEST_DESTINATION} b/{TEST_DESTINATION}\n"
        "new file mode 100644\n"
        "index 0000000..1111111\n"
        "--- /dev/null\n"
        f"+++ b/{TEST_DESTINATION}\n"
        f"@@ -0,0 +1,{len(lines)} @@\n"
        f"{body}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold-source", type=Path, required=True)
    args = parser.parse_args()
    source = args.gold_source.resolve().read_text()
    oracle_patch = (TASK / "solution" / "oracle.patch").read_text()

    config = {
        "instance_id": "bank-statement-parser-long-native-table-migration",
        "repo": "boostmoney/bank-statement-parser",
        "base_commit": "a03ff50b9e6868565ba88be5f7438f4ac7583138",
        "patch": oracle_patch,
        "test_patch": added_file_patch(source),
        "fail_to_pass": [
            "NativeTableMigrationTest::nativeStrategiesProduceStructuredRows",
            "NativeTableMigrationTest::supportedBankFormatsUseCorrectPolicy",
            "NativeTableMigrationTest::nativeSuccessSkipsRemoteExtractor",
            "NativeTableMigrationTest::usageStatusPropagatesToApiAndLogs",
        ],
        "pass_to_pass": [
            "NativeTableMigrationTest::unsupportedFormatsRetainRemoteFallback",
            "NativeTableMigrationTest::legacyDateParsingRemainsStable",
        ],
        "selected_test_files_to_run": [TEST_DESTINATION],
    }
    (TASK / "tests" / "config.json").write_text(json.dumps(config, indent=2) + "\n")

    (ROOT / "instructions" / "long-native-table-migration.md").write_text(
        (TASK / "instruction.md").read_text()
    )
    (ROOT / "gold-tests" / "long-native-table-migration.java").write_text(source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
