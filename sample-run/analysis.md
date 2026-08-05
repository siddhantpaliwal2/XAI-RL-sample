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

## Headline result

Grok solved **21/80 attempts** for a macro mean **pass@1 of 0.2625**,
**pass@3 of 0.3833**, and **pass@10 of 0.5000**. Its task-level result is:

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

The apparent tension between the three means is the main result. Grok has the
highest pass@1 row measured with OpenCode, but its solves are concentrated in
four tasks. GPT-5.6 Sol solves fewer attempts overall while covering six tasks,
so repeated sampling favors GPT.

| OpenCode model | Solves | Mean pass@1 | Mean pass@3 | Mean pass@10 | Tasks with a solve |
|---|---:|---:|---:|---:|---:|
| **Grok 4.5** | **21/80** | **0.263** | 0.383 | 0.500 | 4/8 |
| GPT-5.6 Sol | 16/80 | 0.200 | **0.435** | **0.750** | **6/8** |
| Claude Opus 4.8 | 8/79 | 0.100 | 0.244 | 0.375 | 3/8 |
| Nova Premier | 0/80 | 0.000 | 0.000 | 0.000 | 0/8 |

This is why a single aggregate pass@1 should not be read as a total ordering:
Grok is more repeatable where it wins; GPT is more broadly capable across the
bank.

## August 2026 Claude frontier screen

Claude Opus 5 and Claude Fable 5 were screened with OpenCode 1.18.13 in the
same Daytona task snapshots. These are n=1 cells, so they are current
pass@1 observations rather than stable pass@k estimates.

| Model | credit | doc | fin-tools | phone | FIU | txenr | txenr3 | txenr4 | Solves / valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Claude Opus 5 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 | **6/8** |
| Claude Fable 5 | 0/1 | 0/1 | 0/1 | 0/1 | excluded | 1/1 | 0/1 | 0/1 | **1/7** |

Fable's FIU attempt is excluded, not scored zero. Both the original run and a
single-agent compatibility rerun stopped on the provider's content filter
before verification. The preserved `ContentFilterError`, OpenCode stream, and
Harbor result are under `frontier-exclusions/fable5-xrepo-fiu-latent/`.

Across eight valid Opus trials, the trajectories contain **367 model turns**
and **375 tool calls**. Mean full-trial wall time was **13m 22.5s**, median
**8m 57.0s**, p90 **30m 12.7s**, and the range **7m 19.0s–30m 12.7s**.
Across seven valid Fable trials, the trajectories contain **161 model turns**
and **210 tool calls**. Mean full-trial wall time was **10m 54.4s**, median
**7m 02.5s**, p90 **35m 24.7s**, and the range **3m 47.0s–35m 24.7s**.

Those durations are Harbor `started_at`→`finished_at` trial wall times,
including setup, execution, and verification. Because the trials ran in
parallel, their durations are not summed into an elapsed-time estimate.

## Long-horizon definition and evaluation bar

There is no standard 70-turn or raw-token threshold for a long-horizon task.
The term is used along at least two independent axes:

- [DeepSWE](https://arxiv.org/abs/2607.07946) treats long horizon as a structural
  property: short, natural prompts whose solutions require substantial codebase
  exploration and large, multi-file implementations. It reports tokens, trial
  time, and cost as efficiency measurements, not as the definition.
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

For `long-native-table-migration`, the primary bar is therefore repository-scale
structure: a short six-requirement prompt condenses 62 production commits across
70 files and several dependent subsystems, with an implementation-agnostic
functional verifier. The 70–100 tool-call band is retained as a local
descriptive reference, paired with the requested frontier difficulty gate:
Opus 5 or Fable 5 must fail at least 50% of independent valid attempts. It is
not a maximum or a hard gate; longer traces are welcome. Per-trial model turns,
input/cache/output tokens, cost, and full Harbor wall time are reported
alongside the outcome rather than substituted for it.
No controlled human completion-time baseline was collected, so the task is not
assigned a METR-style hour value. The 62-commit branch establishes real scope,
but commit count and calendar span are not treated as human labor time.
The final jobs use a 9,000-second safety timeout with no step or cost cap, the
same published upper bound used by DeepSWE. This sample's stricter artifact rule
counts only trials whose hidden verifier returned real per-test verdicts;
provider, verifier, network, or operator-timeout runs without verdicts are
excluded from the model denominator.

The four-model long-horizon matrix keeps OpenCode 1.18.13 and the Daytona
snapshot fixed. The valid scored trials use the exact OpenRouter routes for
Opus 5, Fable 5, Grok 4.5, and GPT-5.6 Sol. [AWS's endpoint
catalog](https://docs.aws.amazon.com/bedrock/latest/userguide/models-endpoint-availability.html)
identifies Sol as a [Mantle-only Responses
model](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-openai-gpt-56-sol.html)
with ID `openai.gpt-5.6-sol`; a direct streaming and non-streaming probe in
`us-east-1` succeeded with a short-lived
bearer token derived from the existing AWS CLI credentials. OpenCode 1.18.13,
however, closed the Bedrock transport before its first model turn. Those
zero-turn attempts are excluded as infrastructure failures, and the valid Sol
denominator uses `openrouter/openai/gpt-5.6-sol`. No persistent IAM user or
long-lived API key was created. AWS's same catalog currently lists Grok 4.3,
not Grok 4.5, so Bedrock could not supply the requested exact Grok model.

## Long-horizon measured result

One finalized task was evaluated: `long-native-table-migration`. The final
matrix contains 12 valid attempts, three each for Opus 5, Fable 5, Grok 4.5,
and GPT-5.6 Sol. All four models solved **0/3**, so Opus and Fable each
independently exceed the requested 50% failure threshold. Tool calls ranged
from **80 to 179**, with a conventional 12-trial median of **127**. Nine traces
exceeded the original 70–100 reference band; the checked-in
`long_horizon_results.json` correctly treats that band as descriptive, reports
the difficulty gate as true, and sets overall `qualifies: true`.

pass@k uses `1 − C(n−c, k) / C(n, k)`. Every row has `n=3`, `c=0`:

| Model | Solves | pass@1 | pass@2 | pass@3 | Model turns | Tool calls, median (range) | Trial wall time, mean / median (range) | Cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Claude Opus 5 | 0/3 | 0.000 | 0.000 | 0.000 | 437 | 168 (148–169) | 56m 52.7s / 50m 07.4s (41m 46.6s–78m 44.2s) | $68.42 |
| Claude Fable 5 | 0/3 | 0.000 | 0.000 | 0.000 | 367 | 148 (120–179) | 71m 22.0s / 75m 06.9s (61m 13.5s–77m 45.4s) | $126.01 |
| Grok 4.5 | 0/3 | 0.000 | 0.000 | 0.000 | 110 | 116 (108–134) | 11m 41.9s / 11m 09.2s (10m 11.9s–13m 44.7s) | $4.00 |
| GPT-5.6 Sol | 0/3 | 0.000 | 0.000 | 0.000 | 113 | 90 (80–90) | 8m 24.9s / 8m 41.1s (7m 35.9s–8m 57.8s) | $7.20 |

| Model / attempt | Reward | f2p | p2p | Model turns | Tool calls | Full trial wall time | Input (cached) / output tokens | Cost | Grading |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Opus 5 / 1 | 0 | 0/4 | 1/2 | 150 | 169 | 50m 07.4s | 34.89M (34.89M) / 143.9k | $23.82 | regraded final verifier |
| Opus 5 / 2 | 0 | 1/4 | 1/2 | 154 | 168 | 78m 44.2s | 38.24M (38.24M) / 150.7k | $25.95 | regraded final verifier |
| Opus 5 / 3 | 0 | 0/4 | 1/2 | 133 | 148 | 41m 46.6s | 26.20M (26.20M) / 125.0k | $18.65 | regraded final verifier |
| Fable 5 / 1 | 0 | 0/4 | 2/2 | 89 | 120 | 75m 06.9s | 15.06M (15.06M) / 82.4k | $36.00 | regraded final verifier |
| Fable 5 / 2 | 0 | 0/4 | 1/2 | 165 | 179 | 77m 45.4s | 38.15M (38.15M) / 148.3k | $51.43 | regraded final verifier |
| Fable 5 / 3 | 0 | 0/4 | 2/2 | 113 | 148 | 61m 13.5s | 25.33M (25.33M) / 138.8k | $38.58 | regraded final verifier |
| Grok 4.5 / 1 | 0 | 1/4 | 2/2 | 39 | 134 | 11m 09.2s | 2.80M (2.67M) / 32.7k | $1.27 | original Harbor verifier |
| Grok 4.5 / 2 | 0 | 1/4 | 1/2 | 36 | 116 | 13m 44.7s† | 2.72M (2.52M) / 31.4k | $1.36 | recovered + regraded final verifier |
| Grok 4.5 / 3 | 0 | 1/4 | 2/2 | 35 | 108 | 10m 11.9s | 2.71M (2.50M) / 28.2k | $1.36 | original Harbor verifier |
| GPT-5.6 Sol / 1 | 0 | 1/4 | 1/2 | 37 | 80 | 7m 35.9s | 2.24M (2.24M) / 13.4k | $2.13 | original Harbor verifier |
| GPT-5.6 Sol / 2 | 0 | 1/4 | 1/2 | 40 | 90 | 8m 41.1s | 2.73M (2.73M) / 14.1k | $2.50 | original Harbor verifier |
| GPT-5.6 Sol / 3 | 0 | 1/4 | 1/2 | 36 | 90 | 8m 57.8s | 2.73M (2.73M) / 15.1k | $2.57 | original Harbor verifier |

The matrix used **1,027 model turns**, **1,550 tool calls**, **193.80M input
tokens** (193.26M cached), **923.8k output tokens**, and **$205.63** of model
calls. Independently running trial durations are not summed.

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

For cost accounting, the new work in this XAI extension used **$354.54** of
reported model/API spend: $31.44 for the 80 Grok debugging trials, $76.55 for
the eight-task Opus/Fable screen, $40.92 for superseded long-task calibration,
and $205.63 for the 12 final long-task attempts. That is well below the $1,000
OpenRouter ceiling. Direct Bedrock compatibility probes used the account's AWS
credits and are not included in the OpenRouter total. Daytona infrastructure
charges and inherited Amazon-sample model runs are also excluded.

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
**39,586,944 cached tokens**, **467,658 output tokens**, and **$31.44** in model
cost.

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

## Cost and caveats

- The runtime, turn, token, and cost totals above cover the 80 valid graded
  trajectories. Infrastructure/auth failures encountered while operating the
  wave are excluded from both scores and those valid-trial totals.
- Ten attempts per task are enough to expose systematic zero rows and strong
  concentration, but each individual solve rate still has binomial uncertainty.
- `pass@10` is 1 for any n=10 cell with at least one solve and 0 otherwise. Its
  macro mean is therefore task coverage at this sample size, not an additional
  measure of within-task repeatability.
- Hidden tests assert behavior, not oracle patch identity. Alternative correct
  implementations pass; the failures above are observable output failures, not
  textual-diff mismatches.
