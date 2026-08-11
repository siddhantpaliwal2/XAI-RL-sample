#!/bin/sh
set -u

REPO_DIR=""
for d in /app /testbed; do
    if [ -d "$d/.git" ] && [ -f "$d/src/groovy/com/bankScraper/HelperMethod.groovy" ]; then
        REPO_DIR="$d"
        break
    fi
done
[ -n "$REPO_DIR" ] || { echo "run_script.sh: repository not found" >&2; exit 2; }
cd "$REPO_DIR"

rm -rf /tmp/enterprise-cloud-verifier-classes /tmp/enterprise-cloud-verifier-source
mkdir -p \
    /tmp/enterprise-cloud-verifier-classes \
    /tmp/enterprise-cloud-verifier-source/src/groovy/com/bankScraper \
    /tmp/enterprise-cloud-verifier-source/grails-app/domain/com/bankScraper/bank
cp src/groovy/com/bankScraper/Enums.groovy /tmp/enterprise-cloud-verifier-source/src/groovy/com/bankScraper/
cp src/groovy/com/bankScraper/HelperMethod.groovy /tmp/enterprise-cloud-verifier-source/src/groovy/com/bankScraper/
cp grails-app/domain/com/bankScraper/bank/Document.groovy /tmp/enterprise-cloud-verifier-source/grails-app/domain/com/bankScraper/bank/

GRAILS_HOME="${GRAILS_HOME:-/opt/grails-2.3.11}"
GRAILS_CP="$(find "$GRAILS_HOME" -name '*.jar' ! -name '*sources*' ! -name '*javadoc*' ! -path '*/javaee-web-api/*' -print | tr '\n' ':')"
java -cp "$GRAILS_CP" org.codehaus.groovy.tools.FileSystemCompiler \
    -d /tmp/enterprise-cloud-verifier-classes \
    $(find xai-tests/stubs -name '*.groovy' -print) || exit 0

rm -f /tmp/enterprise-cloud-unit.json
java -cp "/tmp/enterprise-cloud-verifier-classes:${GRAILS_CP}/tmp/enterprise-cloud-verifier-source/src/groovy:/tmp/enterprise-cloud-verifier-source/grails-app/domain:$REPO_DIR/lib/*" \
    groovy.ui.GroovyMain xai-tests/cloud_storage_spec.groovy 2>&1 || true
