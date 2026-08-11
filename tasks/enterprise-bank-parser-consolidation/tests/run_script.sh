#!/bin/sh
set -u

REPO_DIR=""
for d in /app /testbed; do
    if [ -d "$d/.git" ] && [ -f "$d/src/groovy/com/bankScraper/bank/BankTransactionUtil.groovy" ]; then
        REPO_DIR="$d"
        break
    fi
done
[ -n "$REPO_DIR" ] || { echo "run_script.sh: repository not found" >&2; exit 2; }
cd "$REPO_DIR"

rm -rf /tmp/enterprise-verifier-classes /tmp/enterprise-verifier-source
mkdir -p /tmp/enterprise-verifier-classes /tmp/enterprise-verifier-source/com/bankScraper/bank/pdf /tmp/enterprise-verifier-source/com/bankScraper/bank
cp src/groovy/com/bankScraper/bank/BankTransactionUtil.groovy /tmp/enterprise-verifier-source/com/bankScraper/bank/
cp grails-app/services/com/bankScraper/bank/pdf/AndhraBankPdfService.groovy /tmp/enterprise-verifier-source/com/bankScraper/bank/pdf/
cp grails-app/services/com/bankScraper/bank/pdf/BankOfBarodaPdfService.groovy /tmp/enterprise-verifier-source/com/bankScraper/bank/pdf/

GRAILS_HOME="${GRAILS_HOME:-/opt/grails-2.3.11}"
GRAILS_CP="$(find "$GRAILS_HOME" -name '*.jar' -print | tr '\n' ':')"
java -cp "$GRAILS_CP" org.codehaus.groovy.tools.FileSystemCompiler \
    -d /tmp/enterprise-verifier-classes \
    $(find xai-tests/stubs -name '*.groovy' -print) || exit 0

rm -f /tmp/enterprise-unit.json
java -cp "/tmp/enterprise-verifier-classes:${GRAILS_CP}/tmp/enterprise-verifier-source:$REPO_DIR/lib/*" \
    groovy.ui.GroovyMain xai-tests/bank_parser_spec.groovy 2>&1 || true
