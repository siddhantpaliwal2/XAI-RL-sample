#!/usr/bin/env python3
"""Parse Maven Surefire XML into SWE-bench-style per-test verdicts."""

import glob
import json
import os
import sys
import xml.etree.ElementTree as ET


def verdict(testcase):
    for child in testcase:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in ("failure", "error"):
            return "failed"
        if tag == "skipped":
            return "skipped"
    return "passed"


def main():
    report_dirs = sys.argv[1:] or [
        "/app/target/surefire-reports",
        "/testbed/target/surefire-reports",
        "target/surefire-reports",
    ]
    results = {}
    for directory in report_dirs:
        if not os.path.isdir(directory):
            continue
        for path in sorted(glob.glob(os.path.join(directory, "TEST-*.xml"))):
            try:
                root = ET.parse(path).getroot()
            except ET.ParseError:
                continue
            for testcase in root.iter("testcase"):
                name = testcase.get("name")
                classname = testcase.get("classname", "").rsplit(".", 1)[-1]
                if name and classname:
                    results[f"{classname}::{name}"] = verdict(testcase)
    print(json.dumps({"tests": [{"name": k, "status": v} for k, v in results.items()]}))


if __name__ == "__main__":
    main()
