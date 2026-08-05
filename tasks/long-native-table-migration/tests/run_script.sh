#!/bin/sh
set -u

REPO_DIR=""
for d in /app /testbed; do
    if [ -f "$d/pom.xml" ] && [ -d "$d/src/main/java" ]; then
        REPO_DIR="$d"
        break
    fi
done
[ -n "$REPO_DIR" ] || { echo "run_script.sh: Maven repo root not found" >&2; exit 2; }
cd "$REPO_DIR"

rm -rf target/surefire-reports
GOLD_CLASS="NativeTableMigrationTest"

if [ "${1:-}" = "" ]; then
    mvn -o -B -q -Dtest="$GOLD_CLASS" test 2>&1 || true
else
    filter="$(printf '%s' "$1" | sed 's/::/#/g')"
    mvn -o -B -q -Dtest="$filter" test 2>&1 || true
fi
