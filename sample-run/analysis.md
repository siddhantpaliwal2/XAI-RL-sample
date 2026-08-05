# Analysis: Grok 4.5 win conditions and failure modes

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

- The 80 valid trajectories report **$31.44** of model cost, 1,047 agent steps,
  and 357.2 summed agent-minutes. Infrastructure/auth failures encountered while
  operating the wave are excluded from both scores and these valid-trial totals.
- Ten attempts per task are enough to expose systematic zero rows and strong
  concentration, but each individual solve rate still has binomial uncertainty.
- `pass@10` is 1 for any n=10 cell with at least one solve and 0 otherwise. Its
  macro mean is therefore task coverage at this sample size, not an additional
  measure of within-task repeatability.
- Hidden tests assert behavior, not oracle patch identity. Alternative correct
  implementations pass; the failures above are observable output failures, not
  textual-diff mismatches.

