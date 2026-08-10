# Analysis: Grok 4.5, the current Claude frontier, and long-horizon behavior

## Setup

Grok 4.5 was evaluated with OpenCode on all eight latent-defect tasks. Each
task received ten independent attempts in an isolated 2-CPU/4-GB AMD64 Daytona
sandbox. The route was `openrouter/x-ai/grok-4.5`; Harbor injected the hidden
tests only after the agent stopped. All 80 cells produced complete verifier
verdicts. No exception or vacuous trial is included in the scores.

The run used a global 12-sandbox worker pool. Valid attempts are packaged under
`grok-trials/`, including their full trajectory, Harbor result, parsed verifier
output, and raw verifier stdout. `grok_trials.json` is the compact per-attempt
index. A solving trajectory is selected when one exists; otherwise the closest
graded attempt is copied into `trajectories-matrix/` and `trajectories/`.

The long-horizon capability study adds three anonymized production tasks. Each
received eight independent Grok 4.5 attempts and eight independent Claude Opus
5 attempts through OpenCode 1.18.13. Only runs matching the frozen task
checksum, exact route, isolated Daytona environment, single-agent policy, and
complete hidden-verifier output enter the denominator. The earlier
`long-native-table-migration` matrix remains a separate four-model difficulty
control because no measured model solved it.

## Headline result

The strongest capability separation appears on the three new long-horizon
tasks. Grok solves **0/24** attempts while Opus solves **19/24**:

| Task | Required checks | Grok 4.5 | Claude Opus 5 | Opus minus Grok | Learnability result |
|---|---:|---:|---:|---:|---|
| Customer billing-schedule migration | 8 | 0/8 | 7/8 | +87.5 pp | qualifies |
| Top-up billing lifecycle | 11 | 0/8 | 7/8 | +87.5 pp | qualifies |
| S3 datastore measurement | 10 | 0/8 | 5/8 | +62.5 pp | qualifies |
| **Total** | **29** | **0/24** | **19/24** | **+79.2 pp** | **3/3 qualify** |

The learnability criterion accepts tasks where Grok solves one to six of eight
attempts, or where Grok solves zero and a comparable model completes the task.
All three qualify through the comparator-completion path. Opus's repeated
success establishes solvability, while Grok's near-miss traces isolate distinct
gaps in requirement retention, state-machine composition, and cross-boundary
API precision. A task-level 0/8 estimate still has a 95% Wilson interval of
0–32.4%, so the claim rests on the complete eight-attempt evidence and the
comparator result rather than the point estimate alone.

On the eight latent-defect debugging tasks, Grok solved **21/80 attempts** for
a macro mean **pass@1 of 0.2625**, **pass@3 of 0.3833**, and **pass@10 of
0.5000**. Its task-level result is:

| Task | c/n | pass@1 | pass@3 | pass@10 | Mean f2p passed |
|---|---:|---:|---:|---:|---:|
| credit-normalize | 8/10 | 0.800 | 1.000 | 1.000 | 4.8/5 |
| doc-extractors | 0/10 | 0.000 | 0.000 | 0.000 | 4.0/4 |
| financial-tools | 0/10 | 0.000 | 0.000 | 0.000 | 8.0/9 |
| phone-invites | 9/10 | 0.900 | 1.000 | 1.000 | 4.9/5 |
| fiu | 2/10 | 0.200 | 0.533 | 1.000 | 3.7/5 |
| txenrich | 2/10 | 0.200 | 0.533 | 1.000 | 4.4/5 |
| txenrich3 | 0/10 | 0.000 | 0.000 | 0.000 | 3.2/5 |
| txenrich4 | 0/10 | 0.000 | 0.000 | 0.000 | 2.6/5 |

The apparent tension between the three means is the main Grok result. Grok's
solves are concentrated in four tasks, while GPT-5.6 Sol solves fewer attempts
overall but covers six tasks. The completed August frontier screen adds a new
leader: Opus 5 is both more repeatable and more broadly capable than either.

| OpenCode model | Solves | Mean pass@1 | Mean pass@3 | Mean pass@10 | Tasks with a solve |
|---|---:|---:|---:|---:|---:|
| **Claude Opus 5** | **55/80** | **0.688** | **0.834** | **0.875** | **7/8** |
| Claude Fable 5 | 18/63 | 0.290 | 0.582 | 0.667† | 5/7 measured |
| **Grok 4.5** | **21/80** | **0.263** | 0.383 | 0.500 | 4/8 |
| GPT-5.6 Sol | 16/80 | 0.200 | **0.435** | **0.750** | **6/8** |
| Claude Opus 4.8 | 8/79 | 0.100 | 0.244 | 0.375 | 3/8 |
| Nova Premier | 0/80 | 0.000 | 0.000 | 0.000 | 0/8 |

† Fable's pass@10 macro uses its six n=10 cells. Doc extraction is
provider-limited at n=3 and FIU is excluded before inference. This is why a
single aggregate pass@1 should not be read without denominators and task
coverage: Fable edges Grok on pass@1 but not on like-for-like eight-task
coverage, while Grok is more repeatable on its strongest localized tasks.

## August 2026 Claude frontier pass@10

Claude Opus 5 and Claude Fable 5 were evaluated with OpenCode 1.18.13 in the
same Daytona task snapshots. Each available n=10 cell combines the original
exact OpenRouter attempt with nine independently graded attempts on the exact
Bedrock global route. Bedrock fallback was disabled, Fable provider data share
was enabled with approval, and only trials with real hidden-verifier verdicts
enter n.

| Model | credit | doc | fin-tools | phone | FIU | txenr | txenr3 | txenr4 | Solves / valid | pass@1 | pass@3 | pass@10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Claude Opus 5 | 8/10 | 6/10 | 3/10 | 9/10 | 10/10 | 9/10 | 10/10 | 0/10 | **55/80** | **0.6875** | **0.8344** | **0.8750** |
| Claude Fable 5 | 4/10 | 1/3* | 0/10 | 3/10 | excluded | 8/10 | 2/10 | 0/10 | **18/63** | **0.2905** | **0.5821** | **0.6667†** |

The strongest result is Opus's breadth: it solves seven of eight task families,
including 10/10 FIU and txenrich3, while the older OpenCode models solved at
most six. Its one systematic zero is txenrich4. Fable is much less consistent:
it is strong on base txenrich (8/10), but 0/10 on both financial-tools and
txenrich4 and only 2/10 on txenrich3.

Fable FIU is excluded, not scored zero. OpenRouter and Bedrock consistently
filtered the prompt before inference and verification. Fable doc extraction is
provider-limited at n=3, c=1: after a bounded exact-harness sweep across the
OpenRouter, global Bedrock, and U.S. Bedrock routes, more than 100 provider
attempts were filtered before inference and only three produced verifier-valid
trials. pass@10 is therefore undefined for doc; Fable's pass@10 macro uses only
the six cells that reached n=10.

| Model | Valid trials | Model turns | Tool calls | Mean wall time | Median | p90 | Range |
|---|---:|---:|---:|---:|---:|---:|---:|
| Claude Opus 5 | 80 | 3,061 | 3,316 | 12m 46.1s | 10m 14.5s | 23m 28.3s | 5m 04.3s–30m 28.0s |
| Claude Fable 5 | 63 | 1,391 | 1,830 | 16m 01.8s | 12m 37.6s | 35m 24.7s | 3m 47.0s–57m 33.8s |

Those durations are Harbor `started_at`→`finished_at` trial wall times,
including environment setup, agent setup, execution, and verification. The
trials ran concurrently, so independently running durations are not summed.
Filtered calls with no inference contribute no scored failure. The per-attempt
routes, provider attempt IDs, scores, turns, tool calls, tokens, wall time, and
packaged evidence are in `opus5_trials.json`,
`fable5_trials.json`, and `frontier-trials/`.

## Long-horizon definition and evaluation bar

There is no standard 70-turn or raw-token threshold for a long-horizon task.
The term is used along at least two independent axes:

- [DeepSWE](https://arxiv.org/abs/2607.07946) treats long horizon as a structural
  property: short, natural prompts whose solutions require substantial codebase
  exploration and large, multi-file implementations. It reports tokens and
  trial time as efficiency measurements, not as the definition.
- [SWE-Bench Pro](https://arxiv.org/abs/2509.16941) uses an estimated professional
  engineering horizon of hours to days together with multi-file, substantial
  code modifications.
- [SWE-EVO](https://arxiv.org/abs/2512.18470) tests release-level evolution rather
  than a single issue; its reference patch edits 20.9 files and 610.5 lines on
  average, with an average 874-test evaluation surface.
- [METR](https://metr.org/time-horizons/) defines a model time horizon using the
  human-expert completion time at which the model has a target success
  probability. It explicitly does not mean agent elapsed time or action count.

That variation is important. Recent non-coding suites labeled long horizon range
from [over 20 tool calls per task in WildClawBench](https://arxiv.org/abs/2605.10912)
to [318 on average in OSWorld 2.0](https://arxiv.org/abs/2606.29537), while
[TRIP-Bench](https://arxiv.org/abs/2602.01675) reports trajectories reaching
150+ tool calls and 200k+ context tokens. Turn, tool, and token counts are
harness- and domain-dependent diagnostics, not portable cutoffs.

The primary bar for this package is therefore repository-scale structure. The
three capability-gap tasks cross persistence, validation, scheduling, billing,
queueing, IAM, connector, and failure-recovery boundaries. Their packaged
oracles span 17–28 files, and their source evidence covers multi-day production
changes. The separate native-table task condenses 62 production commits across
70 files and several dependent subsystems into a six-requirement prompt.

Turn, tool, token, and wall-time measurements describe the resulting agent
behavior; they are not substituted for structural scope or verifier outcome.
No controlled human completion-time baseline was collected, so the tasks are
not assigned METR-style hour values. Commit count and calendar span establish
provenance and dependency depth, not human labor time.

The capability-gap cohort uses eight valid attempts per model and task. A task
is learnable when Grok solves one to six attempts, or when Grok solves zero and
a comparable model completes the task. The native-table control instead asks
whether Opus 5 or Fable 5 fails at least half of its independent valid attempts.
In both cohorts, only trials whose hidden verifier returns complete per-test
verdicts enter the denominator; provider, verifier, network, and operator
failures without verdicts are excluded.

## Long-horizon capability-gap results

The three new tasks pair authentic multi-boundary implementation scope with a
clear comparator result:

| Task | Packaged oracle | Production evidence | Coupled surface |
|---|---:|---|---|
| Billing schedule | 23 files / 343 LOC | 56 files over 4 days | customer enrollment, invoice periods, ledger, queues, empty usage |
| Top-up lifecycle | 28 files / 1,450 LOC | 21 commits over 6 days | DTO/entity/persistence, hourly scheduling, wallet credit, invoice and overdraft ordering |
| S3 measurement | 17 files / 1,809 LOC | four PRs over 3 days | nested configuration, IAM trust/policy, persistence, connector routing, mirrored DLQ writes |

The S3 changed-LOC count includes a dependency lockfile, so the long-horizon
claim rests on coupled behavioral boundaries, source history, agent traces, and
verifier scope rather than LOC alone. A reward of 1 requires every configured
fail-to-pass and pass-to-pass assertion to pass; partial implementations receive
reward 0.

### Measured effort

Agent wall time excludes sandbox setup and grading. Trial wall time includes
those phases and remote scheduling/provider latency.

| Model / task | Turns, mean | Tool calls, mean | Agent time, median (range) | Trial time, range |
|---|---:|---:|---:|---:|
| Grok / billing | 17.3 | 64.4 | 2.9m (2.8–3.7m) | 3.3m–25.3m |
| Opus / billing | 62.3 | 67.1 | 10.5m (7.9–12.2m) | 8.7m–22.8m |
| Grok / top-up | 54.6 | 161.4 | 13.6m (10.6–19.2m) | 12.0m–58.6m |
| Opus / top-up | 149.9 | 149.6 | 27.5m (21.6–40.2m) | 22.2m–59.7m |
| Grok / S3 | 22.1 | 74.0 | 5.7m (5.2–18.4m) | 5.8m–18.9m |
| Opus / S3 | 109.0 | 111.5 | 25.1m (19.7–36.3m) | 20.3m–37.6m |

Across the 48 valid attempts, the agents produced 3,321 model turns and 5,024
tool calls. Top-up produces the deepest measured trajectories. Billing is
structurally long-horizon even though Grok converges quickly, because all eight
runs reach the same nearly complete but behaviorally incorrect implementation.

### Trace-backed capability gaps

**Billing — requirement retention across a migration.** All eight Grok attempts
pass 7/8 checks and fail schedule replacement. The representative trace
restates that subject and business identity must be preserved, yet both the
create and replacement paths write only `customerId` into
`scheduleParameters`. Opus solves 7/8 attempts. This isolates failure to retain
one cross-module field invariant across a larger migration, not repository
localization or inability to build the code.

**Top-up — state-machine and exact-boundary composition.** Grok's attempts pass
between 3/11 and 9/11 required checks. Every run misses the stable hourly
scheduler ID, while most also lose at least one validation, charging, usage, or
overdraft-ordering invariant. The best run reaches 9/11. Opus solves 7/8
attempts, showing that the complete wallet/scheduler state machine is difficult
but learnable.

**S3 — cross-boundary API-contract precision.** Every Grok attempt misses both
the scoped IAM provisioning/returned-location contract and the
create-persist-return configuration contract; six also miss the mirrored DLQ
behavior. The best runs reach 8/10 checks. Opus solves 5/8 attempts, including
complete implementations across IAM, persistence, connector routing, and
failure handling.

These failures are complementary to the latent-task boundary errors below. In
the long-horizon cohort, Grok usually finds the relevant subsystems and builds a
substantial implementation, but does not preserve every dependent contract
through the final state transition or returned object. The repeated Opus solves
make those omissions useful training signals rather than evidence that the
tasks are unsatisfiable.

Selected trace pairs:

- Billing: [Grok near miss](long-horizon-enterprise-trials/grok45/paigo-customer-billing-schedule-migration/attempt-01/trajectory.json) and [Opus solve](long-horizon-enterprise-trials/opus5/paigo-customer-billing-schedule-migration/attempt-02/trajectory.json)
- Top-up: [Grok best near miss](long-horizon-enterprise-trials/grok45/paigo-top-up-billing-lifecycle/attempt-08/trajectory.json) and [Opus solve](long-horizon-enterprise-trials/opus5/paigo-top-up-billing-lifecycle/attempt-01/trajectory.json)
- S3: [Grok near miss](long-horizon-enterprise-trials/grok45/paigo-s3-datastore-measurement/attempt-01/trajectory.json) and [Opus solve](long-horizon-enterprise-trials/opus5/paigo-s3-datastore-measurement/attempt-01/trajectory.json)

### Fairness and validity

- Untouched bases score 0 and authorized solvability oracles score 1 for all
  three tasks.
- Every selected attempt matches the exact model route, OpenCode version,
  Daytona snapshot, single-agent policy, frozen checksum, and complete verifier
  output.
- A billing audit found an older assertion coupled to positional Nest
  constructor order. It was replaced with a behavioral assertion, fresh
  controls passed, and all 16 attempts on the superseded checksum were excluded.
- Hidden AWS and database assertions run against offline mocks; no external
  operation leaves the verifier process.
- Trajectories are credential-redacted and the published artifact manifest
  records SHA-256 hashes.

The complete evidence is available in
[`long-horizon-enterprise-results.json`](long-horizon-enterprise-results.json),
[`long-horizon-enterprise-trials/`](long-horizon-enterprise-trials/), and
[`long-horizon-enterprise-artifacts-manifest.json`](long-horizon-enterprise-artifacts-manifest.json).

## Native-table migration difficulty control

The earlier `long-native-table-migration` study is retained as a shared
difficulty control rather than a Grok-specific capability gap. Its final
matrix contains 12 valid attempts, three each for Opus 5, Fable 5, Grok 4.5,
and GPT-5.6 Sol. All four models solved **0/3**, so Opus and Fable each
independently exceed the 50% difficulty threshold. Tool calls ranged
from **80 to 179**, with a conventional 12-trial median of **127**. Nine traces
exceeded the original 70–100 reference band; the checked-in
`long_horizon_results.json` correctly treats that band as descriptive, reports
the difficulty gate as true, and sets overall `qualifies: true`.

The control keeps OpenCode 1.18.13 and the Daytona snapshot fixed. Valid scored
trials use the exact OpenRouter routes for all four models. Zero-turn transport
attempts are excluded as infrastructure failures rather than counted as model
failures.

pass@k uses `1 − C(n−c, k) / C(n, k)`. Every row has `n=3`, `c=0`:

| Model | Solves | pass@1 | pass@2 | pass@3 | Model turns | Tool calls, median (range) | Trial wall time, mean / median (range) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Claude Opus 5 | 0/3 | 0.000 | 0.000 | 0.000 | 437 | 168 (148–169) | 56m 52.7s / 50m 07.4s (41m 46.6s–78m 44.2s) |
| Claude Fable 5 | 0/3 | 0.000 | 0.000 | 0.000 | 367 | 148 (120–179) | 71m 22.0s / 75m 06.9s (61m 13.5s–77m 45.4s) |
| Grok 4.5 | 0/3 | 0.000 | 0.000 | 0.000 | 110 | 116 (108–134) | 11m 41.9s / 11m 09.2s (10m 11.9s–13m 44.7s) |
| GPT-5.6 Sol | 0/3 | 0.000 | 0.000 | 0.000 | 113 | 90 (80–90) | 8m 24.9s / 8m 41.1s (7m 35.9s–8m 57.8s) |

| Model / attempt | Reward | f2p | p2p | Model turns | Tool calls | Full trial wall time | Input (cached) / output tokens | Grading |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Opus 5 / 1 | 0 | 0/4 | 1/2 | 150 | 169 | 50m 07.4s | 34.89M (34.89M) / 143.9k | regraded final verifier |
| Opus 5 / 2 | 0 | 1/4 | 1/2 | 154 | 168 | 78m 44.2s | 38.24M (38.24M) / 150.7k | regraded final verifier |
| Opus 5 / 3 | 0 | 0/4 | 1/2 | 133 | 148 | 41m 46.6s | 26.20M (26.20M) / 125.0k | regraded final verifier |
| Fable 5 / 1 | 0 | 0/4 | 2/2 | 89 | 120 | 75m 06.9s | 15.06M (15.06M) / 82.4k | regraded final verifier |
| Fable 5 / 2 | 0 | 0/4 | 1/2 | 165 | 179 | 77m 45.4s | 38.15M (38.15M) / 148.3k | regraded final verifier |
| Fable 5 / 3 | 0 | 0/4 | 2/2 | 113 | 148 | 61m 13.5s | 25.33M (25.33M) / 138.8k | regraded final verifier |
| Grok 4.5 / 1 | 0 | 1/4 | 2/2 | 39 | 134 | 11m 09.2s | 2.80M (2.67M) / 32.7k | original Harbor verifier |
| Grok 4.5 / 2 | 0 | 1/4 | 1/2 | 36 | 116 | 13m 44.7s† | 2.72M (2.52M) / 31.4k | recovered + regraded final verifier |
| Grok 4.5 / 3 | 0 | 1/4 | 2/2 | 35 | 108 | 10m 11.9s | 2.71M (2.50M) / 28.2k | original Harbor verifier |
| GPT-5.6 Sol / 1 | 0 | 1/4 | 1/2 | 37 | 80 | 7m 35.9s | 2.24M (2.24M) / 13.4k | original Harbor verifier |
| GPT-5.6 Sol / 2 | 0 | 1/4 | 1/2 | 40 | 90 | 8m 41.1s | 2.73M (2.73M) / 14.1k | original Harbor verifier |
| GPT-5.6 Sol / 3 | 0 | 1/4 | 1/2 | 36 | 90 | 8m 57.8s | 2.73M (2.73M) / 15.1k | original Harbor verifier |

The matrix used **1,027 model turns**, **1,550 tool calls**, **193.80M input
tokens** (193.26M cached), and **923.8k output tokens**. Independently running
trial durations are not summed.

† Eleven durations are full Harbor `started_at`→`finished_at` wall time,
including environment setup, agent setup, agent execution, and verification.
In one Grok trial the agent command exited successfully but Harbor stalled while
collecting the finished Daytona sandbox. Its 13m 44.7s value is Harbor start to
the recovered agent-completion timestamp, conservatively excluding the
post-agent collection stall; `duration_basis` records that distinction.

The regrade was necessary for artifact validity, not to change the task after
seeing model behavior. The original hidden helper directly called concrete
setter names; valid wiring refactors removed those setters, causing the test
class itself to fail compilation. The repaired helper discovers compatible
services and injects dependencies by type through either setters or fields.
The untouched base still scores 0, the historical oracle still scores 1, and
an alternate oracle with all seven concrete dependency setters removed also
scores 1. All six Opus/Fable candidate worktrees then executed the final
six-test suite and remained reward 0; the Grok and Sol trials ran only after
that verifier was frozen. Regrade provenance is explicit in every packaged
trial index, and the prompt-to-test audit is preserved under
`long-horizon-controls/fairness-audit.md`.

## Turn, tool, and wall-clock profile

The packaged artifacts retain enough timing and trajectory metadata to measure
the run directly. A **model turn** here is an agent-sourced OpenCode trajectory
step; every such step records exactly one LLM call. Each attempt also has one
initial user instruction step, so the 80 trajectories contain **967 model
turns** and **1,047 total trajectory steps**. They contain **2,521 tool calls**.

The per-trial `duration_seconds` value is full trial wall time from Harbor's
`started_at` to `finished_at`, including environment setup, agent setup, agent
execution, and verification. The mean trial took **4m 27.9s**, the median **3m
52.0s**, and the 90th percentile **8m 33.5s**; the range was **1m 28.5s to 15m
14.5s**.

Because the trials ran concurrently, end-to-end elapsed time is measured from
the first valid trial start at `2026-08-05T01:55:54.926Z` to the last finish at
`2026-08-05T03:04:23.728Z`. That observed valid-trial wall-clock envelope was
**1h 08m 28.8s**. Peak observed concurrency was **12**, matching the
worker-pool limit. This envelope does not include
infrastructure/auth failures excluded from the valid set or any operator time
before the first valid trial and after the last.

| Task | Model turns | Mean turns / attempt | Mean trial time | Trial-time range |
|---|---:|---:|---:|---:|
| credit-normalize | 109 | 10.9 | 3.12m | 2.48-3.95m |
| doc-extractors | 91 | 9.1 | 1.89m | 1.59-2.39m |
| financial-tools | 82 | 8.2 | 1.70m | 1.48-1.85m |
| phone-invites | 80 | 8.0 | 2.09m | 1.80-2.32m |
| fiu | 154 | 15.4 | 5.44m | 4.14-7.49m |
| txenrich | 142 | 14.2 | 6.77m | 5.51-10.20m |
| txenrich3 | 143 | 14.3 | 4.89m | 3.78-5.82m |
| txenrich4 | 166 | 16.6 | 9.81m | 7.53-15.24m |
| **All trials** | **967** | **12.1** | **4.47m** | **1.48-15.24m** |

The phase timestamps put the mean trial at 2.2s of environment setup, 20.5s
of agent setup, 234.6s of agent execution, and 6.6s of verification, with the
small remainder in handoffs between phases. Solved attempts were shorter on
average than unsolved attempts (**10.6 vs. 12.6 model turns** and **3.07m vs.
4.96m**), though that comparison is confounded by task difficulty rather than
being a causal measure of solution efficiency.

The same valid trajectories report **46,841,681 input tokens**, including
**39,586,944 cached tokens** and **467,658 output tokens**.

## Grok's win conditions

### 1. A small number of named helpers with behaviorally direct symptoms

Credit-normalize and phone-invites account for **17 of Grok's 21 solves**.
Both tasks localize to a few small Python helpers, and each symptom maps to a
case-fold, slice, regex anchor, or canonicalization branch that can be replayed
directly.

The representative credit trace reaches the correct `normalize.py` and
`junk_filter.py` helpers, tests the reported shapes, and fixes all five hidden
defects in 11 steps. Eight attempts do this completely. The only miss in the
other two attempts is the digit-leading-creditor end anchor.

Phone-invites is even more stable: nine attempts fix the default-region order,
the `00` prefix slice, legacy loan labels, and canonical IDs. The one failed
attempt is exactly one hidden test short: it does not preserve the default
interpretation when no candidate region validates.

### 2. Cross-file work succeeds when every defect leaves a strong local anomaly

Two FIU attempts solve all five Java defects. The selected solve changes five
distinct behaviors: UUID width, 24-hour timestamp formatting, URL-safe Base64,
the segment after `@`, and whitespace emptiness. The trajectory searches
utilities first, follows usages, runs Maven, and checks each family rather than
stopping after the two ticket examples.

The successful txenrich attempts similarly fix all five literal/index defects
across HDFC and ICICI. They are not just lucky final patches: their traces
construct DataFrame replays for the statement layouts and explicitly check the
adjacent non-regression boundaries.

### 3. Fast hypothesis-to-replay loops

The successful small-task traces are short: credit solves take 9–16 steps and
phone solves 7–11. Grok is effective when it can turn the symptom into a
single-input replay, observe the wrong output, change one localized rule, and
rerun the replay. This is a real capability separation from Nova Premier's
zero-solve row: Grok changes behavior on every task and reaches reward on four;
Nova's representative traces mostly edit plausible nearby code and trust the
already-green visible suite.

## Load-bearing failures

### Doc-extractors: every reported defect fixed, every attempt over-corrects

All ten attempts pass all **4/4 fail-to-pass tests**, yet all ten score zero
because they break a pass-to-pass boundary. Every attempt changes the rent-roll
minimum to accept a single rent line. The instruction says the smallest valid
roll has two rows; the correct edit is `count >= 2`. Grok's selected trace uses
`count >= 1`, so the hidden single-line pin fails.

Seven attempts also admit sub-floor appraisals, and seven admit sub-minimum HUD
loans. This is the clearest failure mode in the set: Grok recognizes the right
functions and the inclusive-boundary theme, but generalizes “accept the edge”
past the domain floor. GPT-5.6 and Opus representative solves both explicitly
derive the two-row minimum and test the value immediately below each floor.

### Financial-tools: one universal needle

Every attempt finishes at **8/9 f2p and 14/14 p2p**. All ten miss the same
test: a single 90-day-late item must count as severe delinquency. The planted
guard is `late_90 > 1`; the correct boundary is `> 0`. Grok consistently fixes
the other four families, including the two-observation volatility and 75%
utilization boundaries, but its traces do not follow the severe-delinquency
signal to the sibling call sites that pin this last operator.

### Txenrich3: right symptom family, wrong bank

All ten attempts miss the one-rupee mandate sentinel, and eight also miss the
six-digit cheque width. The closest trace claims to fix the mandate comparison
in Bank of Maharashtra, but the planted defect is the adjacent `eq(2)` rule in
IndusInd. That attempt ends 4/5 with no regressions: it understood the failure
class yet localized the patch to a different bank implementation. By contrast,
the GPT and Opus solving traces edit the IndusInd and IDBI rules named by the
actual narration shapes.

### Txenrich4: breadth without the decisive PNB edit

No attempt solves the broadest task. The PNB NEFT payee test fails in **10/10**
attempts, the Canara UPI payee in 7/10, the cheque-width boundary in 5/10, and
the cleared-cheque segment in 2/10. The selected 18-step trace is revealing: it
builds many Canara and PNB replays, modifies both files, and confidently reports
all five findings fixed, but it never changes PNB's single-capture-group
`py_extract(..., index=1)` defect. Its added PNB work instead expands several
UPI heuristics. More exploration did not produce better localization; the
34-step attempt also scores 0.

### Txenrich: repair plus restraint is the gate

Grok repairs most of the five target defects, but eight attempts break the
15-character cheque-remark pin and three break the non-zero 16-character pin.
Only attempts 9 and 10 both repair the target boundary and preserve those
adjacent cases. This is the same precision problem as doc-extractors, expressed
through a regex/length rule instead of an inequality.

## Trace comparison: Grok vs GPT-5.6 vs Opus 4.8

The models separate less on whether they find relevant code than on what they
use as a stopping condition.

- **Grok** often stops after every named symptom has a plausible patch and its
  self-written examples pass. Its final summaries are confident even on the
  zero-reward traces. The unseen failures come from an adjacent boundary it did
  not test or from patching the right pattern in the wrong bank.
- **GPT-5.6** is less repeatable on Grok's two best tasks, but its representative
  solves more often include direct checks on both sides of a boundary. That is
  why it covers doc-extractors and txenrich3 while Grok does not, producing the
  stronger pass@3/pass@10 despite the lower pass@1.
- **Opus 4.8** uses longer repository-reading traces and has the lowest of the
  three pass@1 values. Its coverage is complementary to Grok: Opus solves
  doc-extractors and txenrich3, where Grok is 0/20, while Grok dominates credit,
  phone, and FIU, where the OpenCode+Opus row has no solves.

The practical ensemble implication is straightforward: Grok is a strong first
attempt for localized normalization/canonicalization work, while a GPT retry is
more valuable than another Grok sample after Grok has repeatedly failed a
semantic-boundary or multi-bank task.

## Caveats

- The runtime, turn, and token totals above cover the 80 valid graded debugging
  trajectories. Infrastructure/auth failures are excluded from both scores and
  valid-trial totals.
- Ten attempts per task are enough to expose systematic zero rows and strong
  concentration, but each individual solve rate still has binomial uncertainty.
- `pass@10` is 1 for any n=10 cell with at least one solve and 0 otherwise. Its
  macro mean is therefore task coverage at this sample size, not an additional
  measure of within-task repeatability.
- Hidden tests assert behavior, not oracle patch identity. Alternative correct
  implementations pass; the failures above are observable output failures, not
  textual-diff mismatches.
