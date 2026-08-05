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
- `sample-run/results.md` — Grok task-level pass@1/pass@3/pass@10
- `sample-run/analysis.md` — Grok vs GPT-5.6/Opus/Nova win conditions
- `sample-run/grok_trials.json` — compact index of all 80 valid attempts
- `sample-run/grok-trials/` — per-attempt result, verifier output, and trajectory
- `sample-run/trajectories*/` — full agent trajectories per cell
- `gold-tests/`, `instructions/` — readable copies of the hidden test suites
  and agent-facing prompts
