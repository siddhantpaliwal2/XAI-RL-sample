# RL task-bank evaluation package — getting started

This folder (`xai-rl-sample`) contains the tasks, gold tests, the expanded
frontier pass@k matrix, the Grok 4.5 analysis, and all 80 Grok trajectories.
The companion `rl-repositories` share contains the three production codebases
the tasks are built on.

## 1. Build the three base images from source (~10 min total)

```sh
cd rl-repositories
docker build -t loangenus-repo:v1 loangenus
docker build -t txenrich-repo:v1 -f transaction-enrichment-python/Dockerfile.repo transaction-enrichment-python
cd ../xai-rl-sample
docker build -t fiu-repo:v1 -f tasks/xrepo-fiu-latent/environment/Dockerfile.repo ../rl-repositories/fiu_adapter
```

(Pre-built linux/amd64 image tarballs are also available from the maintainer
on request if you prefer not to build.)

## 2. Verify a task end-to-end (no model calls, ~2 min)

```sh
cd xai-rl-sample
docker build -t latent-credit-normalize tasks/latent-credit-normalize/environment
# null run - expect "reward: 0":
docker run --rm -v "$PWD/tasks/latent-credit-normalize/tests":/vt:ro \
  latent-credit-normalize sh /vt/test.sh
# oracle run - expect "reward: 1":
docker run --rm -v "$PWD/tasks/latent-credit-normalize/tests":/vt:ro \
  -v "$PWD/tasks/latent-credit-normalize/solution":/vs:ro \
  latent-credit-normalize sh -c 'sh /vs/solve.sh && sh /vt/test.sh'
```

## 3. Re-run the Grok 4.5 matrix on Daytona

The runner is resumable and bounds the entire matrix to 12 concurrent Daytona
sandboxes. It reuses every existing valid verifier result and retries only
missing or infrastructure-failed cells. Create an env file outside the repo:

```sh
DAYTONA_API_KEY=...
DAYTONA_API_URL=https://app.daytona.io/api
OPENROUTER_API_KEY=...
```

The Daytona account must contain the eight 4-GB snapshots named in
`harness/run_grok_daytona.py`. Then run:

```sh
python3 harness/run_grok_daytona.py \
  --env-file /absolute/path/to/daytona-openrouter.env \
  --concurrency 12 --attempts 10 --retries 2
python3 harness/collect_grok_results.py
```

The collector requires exactly ten valid attempts per task before it updates
the score files, so partial or exception trials cannot enter the matrix.

## 4. Where to look

- `README.md` — task format, gates, and the measured 9-model × 5-harness
  pass@k matrix
- `sample-run/analysis.md` — task-level results, effort, failure modes, and
  capability conclusions
- `sample-run/indexes/grok_trials.json` — compact index of all 80 valid attempts
- `sample-run/indexes/` — compact scored-result and per-attempt indexes
- `sample-run/controls/` — control and exclusion summaries
- `sample-run/checkpoints/` — interim calibration and fairness checkpoints
- `sample-run/manifests/` — packaged-artifact manifests
- `sample-run/run-summaries/` and `sample-run/ledgers/` — resumable run state
- `sample-run/bug-injection-trials/grok45/` — per-attempt result, verifier output, and trajectory
- `sample-run/enterprise-long-horizon-trials/{grok45,opus5}/` — the three
  long-horizon task cohorts, separated by model
- `sample-run/trajectories*/` — full agent trajectories per cell
- `tasks/*/instruction.md` — canonical agent-facing prompts
- `gold-tests/` — readable copies of the hidden test suites

## 5. Historical task authoring

`historical_tasks.json` records immutable base and target commits, narrow
oracle path allowlists, stable regression-test paths, and hidden behavioral
test sources. Source repositories are intentionally not part of this Git
repository.

After reviewing a task's manifest boundary, materialize it with:

```sh
python3 harness/package_historical_task.py TASK --git-dir /path/to/repository.git
```

The packager writes only `tasks/TASK/solution/oracle.patch` and the generated
SWE-bench-style `tests/config.json`. `harness/audit_enterprise_tasks.py` checks
that oracle and verifier patches stay inside their allowlists, verifies the
selected remote null/oracle controls, and scans the package for recognized
credential forms.

Hidden verifier patches must add files under a reserved namespace
(`*.gold.spec.ts` or `xai-tests/`). They may not edit an existing candidate
file or add a conventional test filename that an agent could reasonably
create. The audit enforces this rule.

For tasks whose oracle is already generated, refresh reviewed local synthetic
tests without reopening the private export:

```sh
python3 harness/package_historical_task.py TASK --local-tests-only
```

Previously generated, added-only historical gold files named in
`extra_git_test_files` are preserved byte-for-byte. Historical edits in
`test_paths` still require the source Git export. Keep source exports, private
project context, raw model trajectories, credentials, and Daytona snapshot
inputs out of this repository. Generated patches reproduce code for evaluation
and may require source-owner authorization before distribution.
