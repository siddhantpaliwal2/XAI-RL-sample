# Reproducing the XAI RL evaluation

This repository contains the complete task packages, hidden verifiers, oracle
solutions, result indexes, and packaged trajectories for eight bug-injection
debugging tasks and three enterprise long-horizon tasks. The original source
repositories are not required. Twelve sealed linux/amd64 base images provide
the exact pre-task code and installed dependencies without exposing Git
history or private repository access.

The separate native-table migration task is included as a difficulty control.
It is not part of the 11-task headline denominator.

## 1. Access and prerequisites

You need:

- Docker with linux/amd64 support
- AWS CLI credentials that can pull from the private ECR repositories below
- Python 3.11 or newer and `uv`
- Harbor 0.18.0 for model runs
- Daytona access to the named global snapshots used by the runners
- OpenRouter credentials for Grok 4.5 and AWS Bedrock credentials for Claude
  Opus 5

Ask the maintainer for ECR pull access. The principal needs
`ecr:GetAuthorizationToken`, `ecr:BatchCheckLayerAvailability`,
`ecr:GetDownloadUrlForLayer`, and `ecr:BatchGetImage`. Source-repository access
is not needed.

Install the exact runner version:

```sh
uv tool install 'harbor==0.18.0'
```

## 2. Install the sealed base images

From the repository root, run:

```sh
./harness/bootstrap_base_images.sh
```

The script authenticates to private ECR, pulls every image by immutable digest,
tags it with the local name expected by the task Dockerfiles, and rejects any
image that is not linux/amd64. To use a named AWS profile without changing the
script:

```sh
XAI_AWS_PROFILE=my-profile ./harness/bootstrap_base_images.sh
```

| Local base image | Packaged tasks |
|---|---|
| `loangenus-repo:v1` | credit normalization, document extraction, financial tools, phone invites |
| `fiu-repo:v1` | FIU boundary debugging |
| `txenrich-repo:v1` | transaction enrichment, transaction enrichment 3, transaction enrichment 4 |
| `enterprise-backend-eng504-billing-base:v1` | customer billing-schedule migration |
| `enterprise-backend-eng504-identity-base:v1` | customer identity migration |
| `enterprise-backend-eng830-base:v1` | dimension pricing tiers |
| `enterprise-backend-eng1167-base:v1` | top-up billing lifecycle |
| `enterprise-backend-eng411-base:v1` | S3 datastore measurement |
| `enterprise-state-machine-email2197-base:v1` | email inbox infrastructure |
| `enterprise-bank-parser-base:v1` | bank parser consolidation |
| `enterprise-google-cloud-storage-base:v1` | cloud-storage migration |
| `bank-statement-parser-repo:v1` | native-table migration difficulty control |

The digest pins are in `harness/bootstrap_base_images.sh`. They are the
reproducibility boundary; do not replace them with floating tags.

## 3. Verify every task without model calls

Run all 17 packaged task controls, including the 11 headline tasks, the five
additional enterprise cohorts, and the native-table difficulty control:

```sh
./harness/verify_packaged_controls.sh
```

For every task, the untouched image must report `reward: 0`, and applying the
packaged oracle must report `reward: 1`. The expected final line is:

```text
All 17 packaged task controls passed: untouched reward 0, oracle reward 1.
```

These checks prove that the public task package, sealed base, hidden verifier,
and oracle agree before any stochastic model calls are made.

## 4. Daytona snapshot requirement

The published results used one isolated Daytona sandbox per attempt. The
runner files contain the exact global snapshot names:

- `harness/run_grok_daytona.py` for the eight 4-GB bug-injection snapshots
- `harness/run_enterprise_daytona.py` for the three 8-GB enterprise snapshots
- `harness/run_frontier_daytona.py` for the native-table difficulty control

The recipient's Daytona organization must be allowed to resolve those global
snapshot names. If it cannot, request snapshot sharing from the maintainer
before starting model calls. The ECR images are sufficient for local Docker
controls, but private ECR access alone does not grant Daytona snapshot access.

Create an environment file outside this repository. Use only the credentials
needed by the routes you are running:

```sh
DAYTONA_API_KEY=...
DAYTONA_API_URL=https://app.daytona.io/api
OPENROUTER_API_KEY=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...
AWS_REGION=us-east-1
```

Do not commit this file.

## 5. Re-run the eight bug-injection tasks

Grok 4.5 used ten independent OpenRouter attempts per task, OpenCode 1.18.13,
and a global pool of at most 12 Daytona sandboxes:

```sh
python3 harness/run_grok_daytona.py \
  --env-file /absolute/path/to/daytona-models.env \
  --agent-version 1.18.13 \
  --attempts 10 \
  --concurrency 12 \
  --retries 2 \
  --jobs-dir results/bug-grok45
```

The reported Claude Opus 5 pass@10 cohort combines one exact OpenRouter attempt
and nine exact Bedrock global-route attempts per task. Run the two route groups
separately so provider provenance remains visible:

```sh
python3 harness/run_frontier_daytona.py \
  --env-file /absolute/path/to/daytona-models.env \
  --model opus5-openrouter=openrouter/anthropic/claude-opus-5 \
  --attempts 1 \
  --concurrency 8 \
  --agent-version 1.18.13 \
  --run-id reproduce-bug-opus5-openrouter \
  --jobs-dir results/bug-opus5-openrouter

python3 harness/run_frontier_daytona.py \
  --env-file /absolute/path/to/daytona-models.env \
  --model opus5-bedrock=amazon-bedrock/global.anthropic.claude-opus-5 \
  --attempts 9 \
  --concurrency 12 \
  --agent-version 1.18.13 \
  --run-id reproduce-bug-opus5-bedrock \
  --jobs-dir results/bug-opus5-bedrock
```

Summarize the complete cells with the same pass@1, pass@3, and pass@10 schema
used for the ten-attempt bug-task cohort in the report:

```sh
python3 harness/summarize_reproduction.py \
  --expected-attempts 10 \
  --k 1,3,10 \
  results/bug-grok45 \
  results/bug-opus5-openrouter \
  results/bug-opus5-bedrock
```

## 6. Re-run the three enterprise long-horizon tasks

Both models used OpenCode 1.18.13, a denied task/subagent tool, eight
independent attempts per task, exact routes, and complete hidden-verifier
output. The runner enforces the task checksum, route, snapshot, agent version,
and single-agent policy before reusing an existing result.

Run Grok 4.5:

```sh
python3 harness/run_enterprise_daytona.py \
  --env-file /absolute/path/to/daytona-models.env \
  --model grok45=openrouter/x-ai/grok-4.5 \
  --task enterprise-customer-billing-schedule-migration \
  --task enterprise-top-up-billing-lifecycle \
  --task enterprise-s3-datastore-measurement \
  --attempts 8 \
  --concurrency 6 \
  --retries 2 \
  --agent-version 1.18.13 \
  --run-id reproduce-enterprise-grok45 \
  --jobs-dir results/enterprise-grok45 \
  --ledger results/enterprise-grok45-ledger.jsonl
```

Run Claude Opus 5:

```sh
python3 harness/run_enterprise_daytona.py \
  --env-file /absolute/path/to/daytona-models.env \
  --model opus5=amazon-bedrock/global.anthropic.claude-opus-5 \
  --task enterprise-customer-billing-schedule-migration \
  --task enterprise-top-up-billing-lifecycle \
  --task enterprise-s3-datastore-measurement \
  --attempts 8 \
  --concurrency 6 \
  --retries 2 \
  --agent-version 1.18.13 \
  --run-id reproduce-enterprise-opus5 \
  --jobs-dir results/enterprise-opus5 \
  --ledger results/enterprise-opus5-ledger.jsonl
```

Then generate the uniform pass@k table:

```sh
python3 harness/summarize_reproduction.py \
  --expected-attempts 8 \
  results/enterprise-grok45 \
  results/enterprise-opus5
```

Only attempts with `exception_info: null`, a binary reward, and real verifier
output belong in the denominator. Infrastructure and provider failures must be
retried, not scored as model failures.

## 7. Optional native-table difficulty control

The separate control used three attempts per model and the same OpenCode
version:

```sh
python3 harness/run_frontier_daytona.py \
  --env-file /absolute/path/to/daytona-models.env \
  --model grok45=openrouter/x-ai/grok-4.5 \
  --model opus5=openrouter/anthropic/claude-opus-5 \
  --task long-native-table-migration \
  --attempts 3 \
  --concurrency 6 \
  --agent-version 1.18.13 \
  --run-id reproduce-native-table \
  --jobs-dir results/native-table
```

This control is intentionally reported separately because neither model solved
it in the measured cohort.

## 8. Compare fresh runs with packaged evidence

The compact indexes are under `sample-run/indexes/`. The evidence needed to
audit each result is organized as follows:

- `sample-run/bug-injection-trials/grok45/` for all 80 Grok bug-task attempts
- `sample-run/frontier-trials/opus5/` for the Claude Opus 5 bug-task cohort
- `sample-run/enterprise-long-horizon-trials/grok45/` for the 24 Grok
  enterprise attempts
- `sample-run/enterprise-long-horizon-trials/opus5/` for the 24 Claude Opus 5
  enterprise attempts
- `sample-run/long-horizon-trials/` for the native-table difficulty control
- `sample-run/analysis.md` for pass rates, measured effort, trace examples,
  failure modes, and the capability conclusion

Each packaged attempt includes the trajectory, Harbor result, parsed verifier
output, and raw verifier stdout. Use those files to distinguish model behavior
from setup failures and to compare a fresh stochastic rerun with the published
cohort.
