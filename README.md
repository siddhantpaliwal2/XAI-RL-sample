# Coding RL from Enterprise Codebases

Eight fail-to-pass debugging tasks and four highlighted long-horizon enterprise
tasks mined from real production codebases in Python, Java, TypeScript, and
Groovy. The original debugging tasks plant latent boundary defects; the
migrations and features preserve real base commits and historical multi-file
changes. Agents receive only the repository and an engineering ticket, while
gold tests enter the sandbox only at grade time.

This XAI evaluation package includes the 80-attempt Grok 4.5 debugging pass,
fresh OpenCode measurements for Claude Opus 5 and Claude Fable 5, and a
four-model long-horizon matrix spanning those models plus GPT-5.6 Sol. Every
valid trial runs in an isolated Daytona sandbox and includes its result,
verifier verdicts, turn/tool counts, wall time, and full trajectory under
`sample-run/`.

The two primary trace trees are separated by task type:

- `sample-run/bug-injection-trials/grok45/` contains Grok's 80 attempts on the
  eight bug-injection tasks.
- `sample-run/enterprise-long-horizon-trials/` contains the 24 Grok and 24 Opus
  attempts on the three enterprise long-horizon tasks, split by model.

The formatted evaluation report is available as
[`reports/xai-rl-evaluation-report.pdf`](reports/xai-rl-evaluation-report.pdf).

## What the traces show

Across all three enterprise tasks, Grok 4.5 solved **0/24** attempts and Claude
Opus 5 solved **19/24**. The clearest behavior comparison comes from the top-up
and S3 tasks, where the requirements are explicit and the verifier checks what
the finished workflow does. On those two tasks, Grok solved **0/16** attempts
and Opus solved **12/16**.

Grok usually found the right files and built much of the requested feature. It
was less reliable when one rule or generated value had to remain correct across
every step of the workflow:

- **Apply the rule everywhere.** On top-up billing, Grok's best run passed 9/11
  checks and the matching Opus run passed 11/11. Grok applied validation in
  some entry points but missed others, and the offering-level hourly-job check
  failed in all eight Grok runs.
- **Carry generated values through the full workflow.** On S3 measurement,
  Grok attempt 5 passed 5/10 checks and the matching Opus run passed 10/10.
  Every Grok run failed to return the generated access details and carry them
  through creation and storage; six of eight also failed the bad-record path.
- **Prove the whole behavior before reporting completion.** After the final
  source change, Grok ran a build or test in 9/16 top-up and S3 attempts and
  reviewed the final repository changes in 2/16. Opus did so in 16/16 and
  14/16 respectively. These habits are not the score by themselves, but the
  paired traces show that the missing checks would have exposed the defects.

The training target is practical: list every allowed and rejected case, trace
each generated value through creation, return, storage, and final response, and
tie every completion claim to a passing end-to-end check or an inspected final
object. The full evidence and paired traces are in
[`sample-run/analysis.md`](sample-run/analysis.md#what-the-traces-show).

The billing score remains in the results table, but it is not used to explain
Grok's behavior because one check expects a field placement that the prompt
does not require. The bug-injection scores are also reported as outcomes rather
than used for the main capability claim because some prompts intentionally hid
exact boundary values during calibration.

## Table of contents

- [What the traces show](#what-the-traces-show)
- [Task format](#task-format)
- [Enterprise long-horizon tasks](#enterprise-long-horizon-tasks)
- [Gates and measured results for other enterprise tasks](#gates-and-measured-results-for-other-enterprise-tasks)
- [Long-horizon migration task](#long-horizon-migration-task)
- [Frontier-model pass@k matrix](#frontier-model-passk-matrix)
- [How the harness works](#how-the-harness-works)
- [Reproducing these numbers](#reproducing-these-numbers)
- [Optional: verifier sanity check](#optional-verifier-sanity-check-no-agent)

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

The canonical prompt for each task is `tasks/<name>/instruction.md`.
`gold-tests/` holds the extracted source of every task's hidden gold test suite
(the exact code the verifier runs). The gold tests never exist anywhere the
agent can see them at solve time.

One calibration note: `latent-doc-extractors` reward-gates four of its five
planted defects. The fifth (a personal-financial-statement scan floor) is
planted and reversed by the oracle, but no graded test distinguishes it - an
agent that fixes the four gated boundaries scores 1 whether or not it also
finds that one. Every other task gates all five of its defects.

## Enterprise long-horizon tasks

The public sample highlights four repository-scale tasks derived from
authorized production history. Unlike the latent tasks, they do not plant
synthetic bugs: each starts at the exact parent commit of a real feature or
migration and uses a filtered historical change as its solvability oracle.
Prompts state behavioral contracts without company names, commit messages,
ticket IDs, file lists, or implementation hints.

| Task | Change family | Task scope | Opus 5 | Grok 4.5 |
|---|---|---:|---:|---:|
| Customer billing-schedule migration | billing and identity migration | 23 oracle files / 343 LOC | 7/8 | 0/8 |
| Top-up billing lifecycle | wallet and billing lifecycle | 28 oracle files / 1,450 LOC | 7/8 | 0/8 |
| S3 datastore measurement | AWS usage ingestion | 17 oracle files / 1,809 LOC | 5/8 | 0/8 |
| Native table migration | document-extraction migration | 62 commits / 70 production files / ~13,000 added LOC | 0/3 | 0/3 |

The native-table rates were measured on the same frozen three-attempt suite.

Each highlighted task clears the two mandatory mechanical controls: untouched
base reward 0 and historical oracle reward 1. The first three also clear XAI's
learnability gate. The native-table migration is retained as an informative
too-hard control, not presented as XAI-qualified, because no evaluated
comparator solved it. Rerun the enterprise boundary, control, and credential
audit with:

```sh
python3 harness/audit_enterprise_tasks.py
```

Enterprise hidden tests are collision-safe: verifier patches only add reserved
`*.gold.spec.ts` or `xai-tests/` files. They never modify a candidate-visible
test file, so an agent remains free to add or update its own conventional tests.

The Enterprise snapshots are deliberately source-minimized. The parser task carries
only the production parser/service subset needed by the task. The cloud task
contains 23 allowlisted files. Service-account JSON, statement fixtures,
customer data, unrelated configuration, and the historical credential-bearing
transfer script are absent from snapshots, oracle patches, and verifier data.
All verifier fixtures are synthetic.

### Enterprise calibration results

The final long-horizon enterprise study freezes eight valid Grok 4.5 and eight
valid Claude Opus 5 attempts for three anonymized production tasks. Every
attempt used the exact route, OpenCode 1.18.13, a denied task/subagent tool, the
frozen checksum, one isolated Daytona sandbox, and complete hidden-verifier
output.

The complete evidence package covers structural and measured horizon, binary
win conditions, pass rates and confidence intervals, turns, tool calls,
agent/trial wall time, trace-backed failure modes, and verifier fairness:

- [`sample-run/analysis.md`](sample-run/analysis.md#long-horizon-capability-gap-results)
- [`sample-run/indexes/long-horizon-enterprise-results.json`](sample-run/indexes/long-horizon-enterprise-results.json)
- [`sample-run/enterprise-long-horizon-trials/`](sample-run/enterprise-long-horizon-trials/)
- [`sample-run/manifests/long-horizon-enterprise-artifacts-manifest.json`](sample-run/manifests/long-horizon-enterprise-artifacts-manifest.json)

One billing verifier assertion was found to grade positional Nest constructor
order rather than behavior. It was repaired, fresh null/oracle controls passed,
and all 16 attempts on the old checksum were excluded. The final billing rates
above use only the fair checksum. Exploratory attempts and runs on superseded
checksums are not included in the reported denominator.

## Gates and measured results for other enterprise tasks

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

For the focused treatment of the task, verifier, results, and trace-backed
failure patterns, see the
[`Native-table migration difficulty control`](sample-run/analysis.md#native-table-migration-difficulty-control)
section of the analysis.

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

| Requirement | Hidden test | What it checks |
|---:|---|---|
| 1 | `nativeStrategiesProduceStructuredRows` | Grid, box-guided, and row-selected PDFs produce the expected structured cells |
| 2 | `supportedBankFormatsUseCorrectPolicy` | Seven real bank/format fixtures select a working native policy |
| 3 | `nativeSuccessSkipsRemoteExtractor` | Successful native output never calls the remote processor or mapper |
| 4 | `unsupportedFormatsRetainRemoteFallback` | A deliberately unknown bank family reaches the existing remote ML boundary |
| 5 | `usageStatusPropagatesToApiAndLogs` | Native, ML, and fallback states round-trip through statement/account API and log objects |
| 6 | `legacyDateParsingRemainsStable` | Existing date and blank-input behavior remains green |

| Mechanical control | Required tests | Result |
|---|---:|---:|
| Null / untouched base | 0/4 fail-to-pass, 2/2 pass-to-pass | reward 0 |
| Historical oracle | 4/4 fail-to-pass, 2/2 pass-to-pass | reward 1 |
| Alternate field-wired oracle | 4/4 fail-to-pass, 2/2 pass-to-pass | reward 1 |

The native-table study originally used a difficulty-only acceptance gate: at
least one of Opus 5 or Fable 5 had to fail 50% or more of independent valid
attempts. The current XAI gate additionally requires evidence of learnability
when Grok is 0/8, so this task is now retained as a too-hard control rather than
an XAI-qualified training task. The 70–100 tool-call band remains a reference
point, not a maximum or a hard gate. Model outcomes and trace statistics are
packaged separately from the eight-task latent-debugging matrix.

All four long-horizon models use OpenCode 1.18.13 and the same Daytona snapshot.
The scored trials use their exact OpenRouter routes. [AWS's endpoint
catalog](https://docs.aws.amazon.com/bedrock/latest/userguide/models-endpoint-availability.html)
documents GPT-5.6 Sol as a [Mantle-only Responses
model](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-openai-gpt-56-sol.html)
(`openai.gpt-5.6-sol`) and currently lists Grok 4.3 rather than Grok 4.5. A
direct streaming and non-streaming Sol probe against Bedrock Mantle succeeded
with a short-lived bearer token derived from the existing AWS CLI session, but
OpenCode 1.18.13 closed that transport before its first model turn. Those
zero-turn attempts are excluded as infrastructure failures; the valid Sol
denominator therefore uses `openrouter/openai/gpt-5.6-sol`. No persistent IAM
user or API key was created.

Agent observations occasionally include repository configuration files. Before
publication, the packager replaces credential assignments, bearer tokens, and
recognized provider-key forms with `<REDACTED>` while preserving the rest of
each trajectory and its metrics.

### Measured long-horizon result

The final matrix contains three independent attempts for each of four models.
All 12 candidates executed the final six-test verifier and all scored 0, so
Opus 5 and Fable 5 each clear the requested 50% failure gate with a 100%
failure rate. Across the matrix, tool calls ranged from **80 to 179**, with a
median of **127**; nine attempts exceeded the original 70–100 reference band.
The legacy packaged `qualifies` field is `true` under that study's original
difficulty-only rule. Under the current XAI learnability rule, the task is too
hard because no comparator solved it. The longer traces remain useful failure
evidence and are retained rather than rejected.

pass@k uses the unbiased estimator `1 − C(n−c, k) / C(n, k)`. Here every
model has `n=3` and `c=0`, so pass@1, pass@2, and pass@3 are all measured zeros.

| Model | Solves | pass@1 | pass@2 | pass@3 | Model turns, total | Tool calls, median (range) | Trial wall time, mean / median (range) | Cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Claude Opus 5 | 0/3 | 0.000 | 0.000 | 0.000 | 437 | 168 (148–169) | 56m 52.7s / 50m 07.4s (41m 46.6s–78m 44.2s) | $68.42 |
| Claude Fable 5 | 0/3 | 0.000 | 0.000 | 0.000 | 367 | 148 (120–179) | 71m 22.0s / 75m 06.9s (61m 13.5s–77m 45.4s) | $126.01 |
| Grok 4.5 | 0/3 | 0.000 | 0.000 | 0.000 | 110 | 116 (108–134) | 11m 41.9s / 11m 09.2s (10m 11.9s–13m 44.7s) | $4.00 |
| GPT-5.6 Sol | 0/3 | 0.000 | 0.000 | 0.000 | 113 | 90 (80–90) | 8m 24.9s / 8m 41.1s (7m 35.9s–8m 57.8s) | $7.20 |

Wall time is Harbor `started_at` to `finished_at`, including environment setup,
agent setup, agent execution, and verification, for 11 attempts. One Grok run
completed the agent command but Harbor stalled while collecting its finished
sandbox; its conservative 13m 44.7s measurement ends at the recovered agent
completion and is labeled accordingly in the per-attempt JSON. Independently
running durations are not summed. The 12 valid model calls cost **$205.63**.

The final verifier was audited after the wave. Its original helper assumed
specific setter names and could not compile against valid wiring refactors, so
the final helper discovers compatible services and dependencies by type. The
null control remains 0, the historical oracle remains 1, and an alternate
oracle with all seven concrete dependency setters removed also scores 1. All
six Opus/Fable candidate worktrees were then regraded against that final suite;
each executed all six tests and remained reward 0. The subsequent Grok and Sol
runs used that already-frozen verifier. Every packaged attempt records
`grading_provenance`. The full prompt-to-test mapping and verifier repair
rationale are in the
[`Native-table verifier contract`](sample-run/analysis.md#native-table-verifier-contract)
section; raw controls remain under `sample-run/long-horizon-controls/`.

### What "long horizon" means here

There is no field-wide 70-turn or input-token cutoff. The most directly
comparable recent coding benchmark, [DeepSWE](https://arxiv.org/abs/2607.07946),
defines long horizon structurally: a short natural prompt requires substantial
repository exploration and a large, multi-file solution. Its authors explicitly
separate that definition from human wall-clock time, and report output tokens,
agent wall time, and cost as efficiency measures rather than admission gates.
[SWE-Bench Pro](https://arxiv.org/abs/2509.16941) instead describes tasks that
may take a professional engineer hours to days and require substantial
multi-file changes. [SWE-EVO](https://arxiv.org/abs/2512.18470) uses release-level
evolution: its reference patches edit 20.9 files and 610.5 lines on average and
are checked by 874 tests on average. [METR's time-horizon metric](https://metr.org/time-horizons/)
uses estimated human-expert completion time at a given model success probability;
it is not the time the agent runs or the number of actions it takes.

Accordingly, this sample uses two axes. The primary classification is structural:
one short request condenses a real 62-commit, 70-file migration and requires
cross-subsystem discovery, implementation, fallback, diagnostics, and regression
preservation. The empirical difficulty gate is a failure rate of at least 50%
for Opus 5 or Fable 5. The 70–100 tool-call band is a descriptive reference;
traces above it strengthen rather than invalidate the long-horizon evidence.
We also retain and report model turns, input tokens (including cached context),
output tokens, cost, and full-trial wall time, but none of those alone decides
whether the task is long horizon.
Because no engineer completed this packaged task under observation, the sample
does not claim a METR-style human-time horizon; the production branch history
establishes provenance and scope, not a controlled human-hours baseline.
The final agent jobs use the same 9,000-second upper bound published by DeepSWE
and no artificial step or cost cap. The timeout is a safety limit, not part of
the horizon definition; this sample counts a trial only when its hidden verifier
returns real per-test verdicts.

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

### OpenCode harness — 11 models, n≈10 attempts per cell (c/n)

| Model | credit-norm | doc-extract | fin-tools | phone-inv | fiu | txenr | txenr3 | txenr4 | mean pass@1 | mean pass@10 |
|---|---|---|---|---|---|---|---|---|---|---|
| **claude-opus-5** | **8/10** | **6/10** | **3/10** | **9/10** | **10/10** | **9/10** | **10/10** | 0/10 | **0.688** | **0.875** |
| claude-fable-5 | 4/10 | 1/3* | 0/10 | 3/10 | excluded | **8/10** | 2/10 | 0/10 | 0.290 | 0.667† |
| **grok-4.5** | **8/10** | 0/10 | 0/10 | **9/10** | **2/10** | 2/10 | 0/10 | 0/10 | **0.263** | 0.500 |
| gpt-5.6-sol | 4/10 | 5/10 | 0/10 | 1/10 | 1/10 | 4/10 | 1/10 | 0/10 | 0.200 | 0.750 |
| claude-opus-4.8 | 0/10 | 3/10 | 0/10 | 0/10 | 0/9 | 2/10 | 3/10 | 0/10 | 0.100 | 0.375 |
| gpt-5.5 | 1/10 | 0/10 | 0/10 | 7/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0.100 | 0.250 |
| glm-5.2 | 0/8 | 5/10 | 0/9 | 1/10 | 0/10 | 1/10 | 0/10 | 1/13 | 0.097 | 0.471 |
| gemini-3.5-flash | 0/10 | 0/10 | 2/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0.025 | 0.125 |
| deepseek-v4-pro | 0/10 | 0/10 | 0/10 | 1/10 | 0/10 | 0/14 | 0/10 | 0/10 | 0.013 | 0.125 |
| nova-2-lite | 0/10 | 0/10 | 0/9 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0.000 | 0.000 |
| nova-premier | 0/11 | 0/10 | 0/10 | 0/9 | 0/9 | 0/10 | 0/11 | 0/10 | 0.000 | 0.000 |

Opus 5 leads the OpenCode rows on both mean pass@1 and pass@10, solving at
least once on seven of eight tasks. Fable's daggered pass@10 is averaged only
over its six n=10 cells; the provider-limited doc and excluded FIU cells are not
silently converted to failures. Among the earlier July screen, Grok leads on
pass@1 while GPT-5.6 Sol has broader task coverage. The full distinction is
analyzed in `sample-run/analysis.md`.

### Harness axis — flagships across 5 harnesses, n≈3 per cell (c/n)

| Harness + model | credit-norm | doc-extract | fin-tools | phone-inv | fiu | txenr | txenr3 | txenr4 | mean pass@1 | mean pass@3 |
|---|---|---|---|---|---|---|---|---|---|---|
| codex + gpt-5.6-sol | 1/3 | 3/3 | 0/3 | 2/4 | 0/3 | 2/3 | 2/3 | 0/3 | 0.396 | 0.625 |
| claude-code + claude-opus-4.8 | 0/3 | 3/3 | 0/3 | 0/3 | 0/2 | 2/3 | 1/2 | 0/3 | 0.271 | 0.375 |
| terminus-2 + gpt-5.6-sol | 0/3 | 2/3 | 0/3 | 1/4 | 0/3 | 0/3 | 1/3 | 0/3 | 0.156 | 0.344 |
| terminus-2 + claude-opus-4.8 | 0/3 | 0/3 | 0/3 | 0/2 | 0/1 | 1/3 | 1/3 | 0/3 | 0.083 | 0.250 |

The mini-swe-agent gate table above is the third harness reference point:
Opus 4.8 at n=10 per task scores mean pass@1 0.125 there (10 solves across 80
attempts), versus 0.100 on OpenCode, 0.271 on claude-code — the same model
spans a 2.17× solve-rate range across these harnesses. Two structural observations: (1) every task has at
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

**0. Base images (read this first).** Every task Dockerfile starts from a
sealed linux/amd64 image of the pre-task codebase with dependencies installed.
The original source repositories are not needed, and the images are not public
because they contain licensed private source.

**To get access, email [sid@withspecific.com](mailto:sid@withspecific.com)** with
the AWS account ID you want granted. We add that account to the private ECR
registry, usually same business day. Once granted:

```sh
aws sso login            # or otherwise authenticate the granted account
./harness/bootstrap_base_images.sh
```

The script pulls 12 digest-pinned bases, verifies image architecture, and
assigns the local names the task Dockerfiles expect. Together they cover all
17 packaged tasks: the eight bug-injection tasks, all eight enterprise
long-horizon cohorts, and the native-table difficulty control. The five
non-headline enterprise bases are now published alongside the seven original
bases, so every packaged task can be rebuilt from this repository.

See [HANDOFF.md](HANDOFF.md) for the image map, required access, exact model
routes, snapshot names, and complete rerun commands.

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

**4c. Run the enterprise long-horizon gate.** The source-free reproduction
path uses the three sealed enterprise images, the named global Daytona
snapshots, OpenCode 1.18.13, exact Grok 4.5 and Claude Opus 5 routes, a denied
task/subagent tool, and eight attempts per task. The full commands are in
[HANDOFF.md](HANDOFF.md#6-re-run-the-three-enterprise-long-horizon-tasks).

The separate native-table migration difficulty control can be rerun with:

```sh
python3 harness/run_frontier_daytona.py \
  --env-file /tmp/xai-rl-daytona.env \
  --model opus5=openrouter/anthropic/claude-opus-5 \
  --model grok45=openrouter/x-ai/grok-4.5 \
  --task long-native-table-migration --attempts 3 --concurrency 6 \
  --run-id reproduce-native-table --jobs-dir results/native-table \
  --agent-version 1.18.13 --job-timeout 9000
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
