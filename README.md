# Coding RL from Enterprise Codebases

Eight fail-to-pass debugging tasks and one long-horizon feature migration,
all mined from real production fintech codebases in Python and Java. The eight
debugging tasks plant latent single-token boundary defects into otherwise
working repos; the migration condenses a real 62-commit native PDF extraction
branch into one scoped task. Agents receive only the repository and an
engineering ticket, while gold tests enter the sandbox only at grade time.

This XAI evaluation package includes the 80-attempt Grok 4.5 pass plus fresh
OpenCode measurements for Claude Opus 5 and Claude Fable 5. Every valid trial
runs in an isolated Daytona sandbox and includes its result, verifier verdicts,
turn/tool counts, wall time, and full trajectory under `sample-run/`.

## Task format

Each directory under `tasks/` is a
[Harbor](https://github.com/harbor-framework/harbor) task. Harbor is the
Terminal-Bench team's evaluation harness: the directory layout below comes
from Terminal-Bench, not from SWE-bench. The SWE-bench connection is one level
down - the grading config inside `tests/` follows SWE-bench-Pro conventions
(`config.json`'s instance/commit/patch/test fields, and the
run_script + parser pattern) - and the probe agent (mini-swe-agent) comes from
the SWE-bench authors. Layout:

```
tasks/<name>/
├── instruction.md          what the agent reads (symptoms + expected behavior, never the fix)
├── reference_plan.md       author notes: root cause, oracle fix, verifier design
├── task.toml               metadata: difficulty, category, timeouts, resources
├── environment/Dockerfile  FROM <repo base image>; plants the defects; the agent's world
├── solution/solve.sh       gold patch; applies cleanly at base, fixes every defect
└── tests/
    ├── config.json         fail_to_pass[], pass_to_pass[], patch, test_patch (gold tests, injected at grade time)
    ├── test.sh             verifier entrypoint; writes reward 1/0 to /logs/verifier/reward.txt
    ├── run_script.sh       language test runner (pytest / mvn)
    └── parser.py           runner stdout → [{name, status}]
```

A task rewards 1 only when **every** `fail_to_pass` and `pass_to_pass` test
passes - partial fixes score 0.

For convenience, `instructions/` holds a readable copy of every task's
`instruction.md` (one file per task) so the nine agent-facing prompts can be
skimmed side by side, and `gold-tests/` holds the extracted source of every
task's hidden gold test suite (the exact code the verifier runs). The canonical
copies remain `tasks/<name>/instruction.md` and the `test_patch` field inside
`tasks/<name>/tests/config.json`; the gold tests never exist anywhere the agent
can see them at solve time.

One calibration note: `latent-doc-extractors` reward-gates four of its five
planted defects. The fifth (a personal-financial-statement scan floor) is
planted and reversed by the oracle, but no graded test distinguishes it - an
agent that fixes the four gated boundaries scores 1 whether or not it also
finds that one. Every other task gates all five of its defects.

## Gates and measured results

Each latent debugging task clears four gates **in order** - two mechanical
checks, then two model probes. Each gate must pass before the next runs:

| # | Gate | Threshold | What it proves |
|---|---|---|---|
| 1 | Null (nop) | reward 0; every `fail_to_pass` FAILS | the defects are real and the gold tests catch them |
| 2 | Oracle | reward 1 with `solution/solve.sh` | the task is solvable and the verifier is satisfiable |
| 3 | Easiness probe | Sonnet 4.6 × 5 attempts, ≤ 1/5 solved | a mid-tier model can't crack it at baseline |
| 4 | Difficulty probe | Opus 4.8 × 10 attempts, ≤ 4/10 solved | a frontier model fails most of the time |

The order is cost-driven: null/oracle are free (no model calls) and kill
mechanically broken tasks instantly; the Sonnet probe is the cheap screen - if
a mid-tier model solves the task 2+ times out of 5, the defects are greppable
rather than latent and there is no point spending the ~10x more expensive Opus
runs; only tasks that survive Sonnet get the full 10-attempt Opus difficulty
measurement that decides the table below.

Both probes are measured with
**[mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent)** - the minimal
(~100-line agent class) agent from the Princeton/Stanford team behind SWE-bench
and SWE-agent; bash-only, linear history, yet >74% on SWE-bench Verified. We
gate on a deliberately *simple* harness: strong scaffolds
(Claude Code-style agent loops with rich tooling) solve these tasks bimodally
and mask the difficulty signal RL training needs.

A hard task (down to 0/10) is acceptable **only** after a fairness audit:
per-test failures must spread across defects (not one universally-missed
unpinnable assertion), every defect's correct fix must be uniquely derivable
from visible code, and a materially different correct fix must also pass the
verifier. The 0–1/10 tasks below carry that audit in their `reference_plan.md`.

All numbers below are clean runs (zero crashed trials counted; a trial only
counts when the verifier emitted real per-test verdicts). Five tasks were
measured with `harness/run_attempt.py` (mini-swe-agent, canonical
swebench.yaml config, 250-step limit, $3 cost cap per attempt). Three
(`latent-credit-normalize`, `latent-doc-extractors`, `xrepo-fiu-latent`) were
re-gated after their instructions were rewritten into bug-report/ticket form:
same solver and invocation (`mini-swe-agent --yolo --model=…`), run at scale
on Daytona cloud sandboxes (amd64 images of the same task environments; every
image null/oracle-verified first).

| Task | Substrate | Lang | Opus solves/10 | Sonnet solves/5 |
|---|---|---|---|---|
| latent-credit-normalize | loangenus (66k LOC) | Python | 0/10 | 0/5 |
| latent-doc-extractors | loangenus | Python | 4/10 | 0/5 |
| latent-financial-tools | loangenus | Python | 0/10 | 0/5 |
| latent-phone-invites | loangenus | Python | 1/10 | 0/5 |
| xrepo-fiu-latent | fiu_adapter (264 files) | Java | 0/10 | 0/5 |
| xrepo-txenrich-latent | transaction-enrichment | Python | 1/10 | 0/5 |
| xrepo-txenrich3-latent | transaction-enrichment | Python | 4/10 | 0/5 |
| xrepo-txenrich4-latent | transaction-enrichment | Python | 0/10 | 0/5 |

`xrepo-fiu-latent` note: its 0/10 carries the required fairness audit — misses
spread across distinct defects (base64 alphabet 10/10, handle-index 10/10,
UUID-regex precision 4/10, whitespace-emptiness 3/10), each pinned by visible
same-file evidence, and all 10 trials produced full per-test verdicts.



The common failure mode on the hard tasks is instructive: agents fix 3–4 of
the 5 planted defects and consistently miss the same one or two - the reward
signal concentrates exactly on the defects that require cross-code derivation
rather than search.

## Long-horizon migration task

`long-native-table-migration` condenses a real 62-commit production branch
into one feature-development task at its pre-migration base. The branch changed
70 production files and added roughly 13,000 lines across native PDF geometry,
normalized table structures, bank-format policy, service routing, fallback,
and API/persistence diagnostics. The sealed environment retains the repository's
135 statement PDFs and cached fixture data but removes branch history and tests.

The prompt is six numbered requirements, each paired one-to-one with one hidden
verifier method. The verifier discovers policy/configuration objects, native
extractors, and status properties structurally; it executes real fixtures and
observes the existing document-extraction service boundary, so alternative
class names and implementations can pass. It does not compare the submitted
patch with the 62-commit oracle.

| Mechanical control | Required tests | Result |
|---|---:|---:|
| Null / untouched base | 0/4 fail-to-pass, 2/2 pass-to-pass | reward 0 |
| Historical oracle | 4/4 fail-to-pass, 2/2 pass-to-pass | reward 1 |

The long-horizon acceptance gate omits Sonnet. It requires valid Opus 5 and
Fable 5 trials to land around 70–100 tool calls and at least one model to fail
50% or more of independent attempts. Model outcomes and trace statistics are
packaged separately from the eight-task latent-debugging matrix.

## Frontier-model pass@k matrix

Every cell below is measured: one Daytona sandbox per attempt (identical
2-CPU/4-GB amd64 environments), the agent harness named in the table, models
via OpenRouter (Claude via the Anthropic API, Muse Spark via the Meta Model
API). A trial counts toward n only if the verifier emitted real per-test
verdicts. pass@k uses the unbiased estimator
**pass@k = 1 − C(n−c, k) / C(n, k)** over n valid attempts with c solves,
averaged across the eight tasks (k is capped at a cell's n). Full per-trial
data and trajectories: `sample-run/`.

Model selection (July 2026): each lab's latest frontier coding model available
by API — Grok 4.5, GPT-5.6 Sol (Terminal-Bench 2.1 leader) plus GPT-5.5,
Gemini 3.5 Flash (Google's strongest agentic/coding model), GLM-5.2,
DeepSeek V4 Pro, Claude Opus 4.8, and both accessible Amazon Novas. Two configurations were
run but excluded from the matrix after trace review showed their attempts
never actually exercised the model: Meta's Muse Spark 1.1 (a key-forwarding
fault on our side meant its agent errored on auth before doing any work) and
aider + Opus 4.8 (aider sends a `temperature` parameter the Opus 4.8 API
rejects, so every attempt died on the first call). Neither zero is a model
result, so neither is reported as one. Amazon's Nova 2 Pro is preview-gated
(not on OpenRouter or generally on Bedrock) and could not be included.

### Current Claude frontier screen — OpenCode, n=1 per available cell (c/n)

[Claude Opus 5](https://platform.claude.com/docs/en/about-claude/models/whats-new-opus-5)
and [Claude Fable 5](https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5)
were added in August 2026 using the exact OpenRouter routes shown in
`sample-run/*_results.json`, OpenCode 1.18.13, and the same Daytona snapshots.
This is a **one-attempt screening snapshot**, not a stable pass@k estimate;
pass@3 and pass@10 are undefined at n=1.

| Model | credit-norm | doc-extract | fin-tools | phone-inv | fiu | txenr | txenr3 | txenr4 | measured solves | macro pass@1 |
|---|---|---|---|---|---|---|---|---|---:|---:|
| **claude-opus-5** | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 | **6/8** | **0.750** |
| claude-fable-5 | 0/1 | 0/1 | 0/1 | 0/1 | excluded | 1/1 | 0/1 | 0/1 | 1/7 | 0.143 |

Fable's FIU cell is not a zero. The original job (including its retry) and a
single-agent compatibility rerun reached the provider but were blocked by a
`ContentFilterError` before verification. The raw
exception and model log are preserved under `sample-run/frontier-exclusions/`;
the cell has n=0 and is excluded from Fable's macro mean.

The per-trial duration is full Harbor wall time from `started_at` to
`finished_at`, including environment setup, agent setup, execution, and
verification. No independently running durations are summed.

| Model | Valid trials | Model turns | Tool calls | Mean wall time | Median | p90 | Range |
|---|---:|---:|---:|---:|---:|---:|---:|
| claude-opus-5 | 8 | 367 | 375 | 13m 22.5s | 8m 57.0s | 30m 12.7s | 7m 19.0s–30m 12.7s |
| claude-fable-5 | 7 | 161 | 210 | 10m 54.4s | 7m 02.5s | 35m 24.7s | 3m 47.0s–35m 24.7s |

### OpenCode harness — 9 models, n≈10 attempts per cell (c/n)

| Model | credit-norm | doc-extract | fin-tools | phone-inv | fiu | txenr | txenr3 | txenr4 | mean pass@1 | mean pass@10 |
|---|---|---|---|---|---|---|---|---|---|---|
| **grok-4.5** | **8/10** | 0/10 | 0/10 | **9/10** | **2/10** | 2/10 | 0/10 | 0/10 | **0.263** | 0.500 |
| gpt-5.6-sol | 4/10 | 5/10 | 0/10 | 1/10 | 1/10 | 4/10 | 1/10 | 0/10 | 0.200 | 0.750 |
| claude-opus-4.8 | 0/10 | 3/10 | 0/10 | 0/10 | 0/9 | 2/10 | 3/10 | 0/10 | 0.100 | 0.375 |
| gpt-5.5 | 1/10 | 0/10 | 0/10 | 7/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0.100 | 0.250 |
| glm-5.2 | 0/8 | 5/10 | 0/9 | 1/10 | 0/10 | 1/10 | 0/10 | 1/13 | 0.097 | 0.471 |
| gemini-3.5-flash | 0/10 | 0/10 | 2/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0.025 | 0.125 |
| deepseek-v4-pro | 0/10 | 0/10 | 0/10 | 1/10 | 0/10 | 0/14 | 0/10 | 0/10 | 0.013 | 0.125 |
| nova-2-lite | 0/10 | 0/10 | 0/9 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0.000 | 0.000 |
| nova-premier | 0/11 | 0/10 | 0/10 | 0/9 | 0/9 | 0/10 | 0/11 | 0/10 | 0.000 | 0.000 |

Grok leads the OpenCode rows on mean pass@1, but GPT-5.6 Sol leads on
pass@10 because it solves at least once on six tasks versus Grok's four. Grok's
21 solves are highly concentrated in credit-normalize and phone-invites; the
full distinction is analyzed in `sample-run/analysis.md`.

### Harness axis — flagships across 5 harnesses, n≈3 per cell (c/n)

| Harness + model | credit-norm | doc-extract | fin-tools | phone-inv | fiu | txenr | txenr3 | txenr4 | mean pass@1 | mean pass@3 |
|---|---|---|---|---|---|---|---|---|---|---|
| codex + gpt-5.6-sol | 1/3 | 3/3 | 0/3 | 2/4 | 0/3 | 2/3 | 2/3 | 0/3 | 0.396 | 0.625 |
| claude-code + claude-opus-4.8 | 0/3 | 3/3 | 0/3 | 0/3 | 0/2 | 2/3 | 1/2 | 0/3 | 0.271 | 0.375 |
| terminus-2 + gpt-5.6-sol | 0/3 | 2/3 | 0/3 | 1/4 | 0/3 | 0/3 | 1/3 | 0/3 | 0.156 | 0.344 |
| terminus-2 + claude-opus-4.8 | 0/3 | 0/3 | 0/3 | 0/2 | 0/1 | 1/3 | 1/3 | 0/3 | 0.083 | 0.250 |

The mini-swe-agent gate table above is the third harness reference point:
Opus 4.8 at n=10 per task scores mean pass@1 0.075 there, versus 0.100 on
OpenCode, 0.271 on claude-code — the same model spans a 3.6× solve-rate range
on harness choice alone. Two structural observations: (1) every task has at
least one solve from some (model, harness) pair — including txenr4, cracked
only by GLM-5.2 — so no task is unverifiable; (2) `fin-tools` and `txenr4`
hold under 3% pass@1 across all 15 rows, while `doc-extract` is farmable by
the strongest pairs, mapping the bank's difficulty spread at the current
frontier.

## How the harness works

The probe harness is two pieces: **mini-swe-agent** (the solver) and
`harness/run_attempt.py` (the runner that wraps one full attempt end to end).

**The solver.** [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent)
is the minimal agent from the SWE-bench/SWE-agent authors - a single LLM loop
(~100 lines) whose only tool is a bash shell inside the task container. The
runner imports the actual `minisweagent` package; nothing is re-implemented. No file viewers, no search index, no sub-agents -
the model reads code with `grep`/`cat`/`sed` and edits with shell commands.
The harness loads its canonical `swebench.yaml` benchmark config verbatim:
250-step limit, $3 cost cap per attempt, 30-minute wall clock. That weak,
standardized scaffold is the point - it is the same probe the task platform
uses, and difficulty numbers only mean something if everyone measures with the
same agent.

**The runner.** One invocation of `run_attempt.py <task> <attempt-no> <out-dir>`
does the whole lifecycle:

1. Starts a fresh container from the task image (`docker run` of `<task>`),
   working directory `/app` - the planted repo with sealed git history.
2. Instantiates mini-swe-agent against that container with the model from
   `PROBE_MODEL` (default `anthropic/claude-opus-4-8`).
3. Hands it `tasks/<task>/instruction.md` as the task prompt. The agent
   explores and edits `/app` until it submits or hits a limit.
4. Grades in place: copies `tasks/<task>/tests/` into the still-running
   container and executes `test.sh` - this is the first moment the gold tests
   exist anywhere the agent could have touched, so they cannot have been read
   or weakened. `test.sh` applies `config.json`'s `test_patch`, runs the suite,
   and requires every `fail_to_pass` and `pass_to_pass` test to pass.
5. Tears the container down and writes three artifacts to `<out-dir>`:
   `<task>-a<N>.json` (reward 0/1, tests passed, cost, model calls, exit
   status), `<task>-a<N>.traj.json` (the full agent trajectory - every command
   and model message), and `<task>-a<N>.grade.log` (verbatim verifier output,
   including exactly which gold tests failed).

Attempts are independent, so parallelism is just running several invocations
at once (see the concurrency caution below). The solve counts in the table are
literally `grep -c '"reward": 1'` over those result files; the `.grade.log`
files are what we used to see which planted defect stopped each failed run.

## Reproducing these numbers

Everything below assumes Docker is running and you are at the repo root.

**0. Base images (read this first).** Every task Dockerfile starts
`FROM <repo>-repo:v1` (e.g. `loangenus-repo:v1`) - a pre-built image of the
underlying **private** codebase with dependencies installed. The images
(linux/amd64) are distributed via a private Amazon ECR registry - request pull
access from the maintainer, then:

```sh
aws ecr get-login-password --region us-east-1 | docker login --username AWS \
  --password-stdin 237343249281.dkr.ecr.us-east-1.amazonaws.com
for r in loangenus-repo txenrich-repo fiu-repo bank-statement-parser-repo; do
  docker pull 237343249281.dkr.ecr.us-east-1.amazonaws.com/rl-images/$r:v1-amd64
  docker tag  237343249281.dkr.ecr.us-east-1.amazonaws.com/rl-images/$r:v1-amd64 $r:v1
done
```

The images can also be rebuilt from source: the substrate trees live in the
companion `rl-repositories` share, and the exact image recipes are the
`Dockerfile` at each substrate root (loangenus, transaction-enrichment-python),
`tasks/xrepo-fiu-latent/environment/Dockerfile.repo` (fiu_adapter), and
`tasks/long-native-table-migration/environment/Dockerfile.repo`
(bank-statement-parser).

**1. Get an Anthropic API key into your shell** (a probe attempt typically
costs $0.40–1.60 and is hard-capped at $3):

```sh
export ANTHROPIC_API_KEY=sk-ant-...
```

**2. Build a task image:**

```sh
docker build -t latent-credit-normalize tasks/latent-credit-normalize/environment
```

**3. Install the agent harness:**

```sh
uv tool install mini-swe-agent
uv pip install --python "$(uv tool dir)/mini-swe-agent/bin/python" fastapi orjson
```

**4. Run the harness.** One invocation of
`harness/run_attempt.py <task> <attempt-no> <out-dir>` is one complete probe
attempt (container, agent, hidden-verifier grading, artifacts - see "How the
harness works" above).

**4a. Run an individual task** (reproduces one row of the table; image built
per step 2):

```sh
PY="$(uv tool dir)/mini-swe-agent/bin/python"
# difficulty probe (Opus, the default model): 10 attempts
for i in $(seq 1 10); do "$PY" harness/run_attempt.py latent-credit-normalize "$i" results/; done
# easiness probe (Sonnet): 5 attempts
for i in $(seq 1 5); do PROBE_MODEL=anthropic/claude-sonnet-4-6 "$PY" harness/run_attempt.py latent-credit-normalize "$i" results-sonnet/; done
```

Count solves: `grep -l '"reward": 1' results/latent-credit-normalize-a*.json | wc -l`
- that number over 10 is the task's cell in the table.

**4b. Run the eight latent tasks** (reproduces the latent-task table).
Attempts are independent,
so parallelize with `xargs -P`; builds every task image, then fans out
attempts:

```sh
PY="$(uv tool dir)/mini-swe-agent/bin/python"
TASKS="latent-credit-normalize latent-doc-extractors latent-financial-tools latent-phone-invites xrepo-fiu-latent xrepo-txenrich-latent xrepo-txenrich3-latent xrepo-txenrich4-latent"
# Opus pass (10 attempts per task):
for t in $TASKS; do
  docker build -q -t "$t" "tasks/$t/environment"
  for i in $(seq 1 10); do echo "$t $i"; done
done | xargs -P 10 -L 1 sh -c "\"$PY\" harness/run_attempt.py \$0 \$1 results/"
# Sonnet pass (5 attempts per task):
for t in $TASKS; do
  for i in $(seq 1 5); do echo "$t $i"; done
done | PROBE_MODEL=anthropic/claude-sonnet-4-6 xargs -P 10 -L 1 sh -c "\"$PY\" harness/run_attempt.py \$0 \$1 results-sonnet/"
```

Keep concurrent attempts ≤ 15 machine-wide. A trial that crashes under load
records `"reward": null` or a non-`Submitted` exit_status - rerun that attempt
number; never count a crash as a fail.

**4c. Run the long-horizon Daytona gate.** Prepare an env file containing
`DAYTONA_API_KEY`, `DAYTONA_API_URL`, and `OPENROUTER_API_KEY`, pin the source
checkout to the task's base commit, then create the sealed snapshot once:

```sh
HARBOR_PY="$(uv tool dir)/harbor/bin/python"
"$HARBOR_PY" harness/create_long_task_daytona_snapshot.py \
  --repo /path/to/bank-statement-parser-at-base \
  --env-file /tmp/xai-rl-daytona.env
```

Run Opus and Fable attempts through one global worker pool. OpenCode's task
tool is denied so every trajectory is a single-agent run:

```sh
python3 harness/run_frontier_daytona.py \
  --env-file /tmp/xai-rl-daytona.env \
  --model opus5=openrouter/anthropic/claude-opus-5 \
  --model fable5=openrouter/anthropic/claude-fable-5 \
  --task long-native-table-migration --attempts 3 --concurrency 6 \
  --run-id long-native-final-r2 --jobs-dir sample-run/long-raw \
  --agent-version 1.18.13 --disable-task-tool --job-timeout 9000

python3 harness/collect_long_results.py \
  --run-id long-native-final-r2 --expected-attempts 3
```

The runner reuses a cell only after validating the model route, OpenCode
version, Daytona snapshot, task checksum, and real verifier output. A provider
or infrastructure exception is therefore never converted into reward 0.

## Optional: verifier sanity check (no agent)

To confirm a task's mechanics without spending any model calls - the planted
state really fails the gold tests, and the gold fix really passes them - run
the hidden verifier directly:

```sh
# null: no fix applied - expect "reward: 0" and every fail_to_pass FAILED
docker run --rm -v "$PWD/tasks/latent-credit-normalize/tests":/vt:ro \
  latent-credit-normalize sh /vt/test.sh

# oracle: gold fix applied - expect "reward: 1"
docker run --rm -v "$PWD/tasks/latent-credit-normalize/tests":/vt:ro \
  -v "$PWD/tasks/latent-credit-normalize/solution":/vs:ro \
  latent-credit-normalize sh -c 'sh /vs/solve.sh && sh /vt/test.sh'
```
