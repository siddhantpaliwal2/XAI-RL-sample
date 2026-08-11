# Analysis: Grok 4.5, the current Claude frontier, and long-horizon behavior

## Table of contents

- [Setup](#setup)
  - [Bug-injection debugging track: eight tasks](#bug-injection-debugging-track-eight-tasks)
  - [Enterprise long-horizon track: three tasks](#enterprise-long-horizon-track-three-tasks)
  - [Separate native-table difficulty control](#separate-native-table-difficulty-control)
- [Headline result](#headline-result)
  - [Enterprise long-horizon tasks](#enterprise-long-horizon-tasks)
  - [Bug-injection debugging tasks](#bug-injection-debugging-tasks)
- [Long-horizon definition and evaluation bar](#long-horizon-definition-and-evaluation-bar)
- [Long-horizon capability-gap results](#long-horizon-capability-gap-results)
  - [Pass@k results](#passk-results)
  - [Measured effort](#measured-effort)
  - [Grok win conditions on enterprise long-horizon tasks](#grok-win-conditions-on-enterprise-long-horizon-tasks)
  - [Failure modes and model contrast](#failure-modes-and-model-contrast)
    - [Billing: declared invariant, omitted nested field](#billing-declared-invariant-omitted-nested-field)
    - [Top-up: parallel implementations instead of one lifecycle invariant](#top-up-parallel-implementations-instead-of-one-lifecycle-invariant)
    - [S3: correct architecture, non-canonical output string](#s3-correct-architecture-non-canonical-output-string)
  - [Fairness and validity](#fairness-and-validity)
- [Bug-injection debugging analysis](#bug-injection-debugging-analysis)
  - [Bug-task pass@k results](#bug-task-passk-results)
  - [Bug-task measured effort](#bug-task-measured-effort)
  - [Grok win conditions on bug-injection tasks](#grok-win-conditions-on-bug-injection-tasks)
  - [Bug-task failure modes and model contrast](#bug-task-failure-modes-and-model-contrast)
    - [Doc extraction: boundary repair without the negative pin](#doc-extraction-boundary-repair-without-the-negative-pin)
    - [Financial tools: one ticket condition never reaches the diff](#financial-tools-one-ticket-condition-never-reaches-the-diff)
    - [Txenrich: broad regex expansion instead of one exact width](#txenrich-broad-regex-expansion-instead-of-one-exact-width)
    - [Txenrich3: correct symptom family, wrong bank implementation](#txenrich3-correct-symptom-family-wrong-bank-implementation)
    - [Txenrich4: complementary near misses and shared frontier difficulty](#txenrich4-complementary-near-misses-and-shared-frontier-difficulty)
- [Native-table migration difficulty control](#native-table-migration-difficulty-control)
- [Caveats](#caveats)

## Setup

This analysis contains two primary evaluation tracks with different task
construction methods, plus one separate difficulty control. Their denominators
and conclusions are reported separately rather than pooled.

### Bug-injection debugging track: eight tasks

These eight tasks begin with working production code into which narrow latent
boundary defects were deliberately introduced. Agents receive symptom-style
engineering tickets and must repair the planted behavior without breaking
existing functionality. This track measures defect localization, boundary
reasoning, and regression-safe repair; it does not ask agents to implement a
historical feature from scratch.

Grok 4.5 received ten independent OpenCode attempts per task in isolated
2-CPU/4-GB AMD64 Daytona sandboxes. The route was
`openrouter/x-ai/grok-4.5`; Harbor injected the hidden tests only after the
agent stopped. All 80 attempts produced complete verifier verdicts. No
exception or vacuous trial is included in the scores.

The run used a global 12-sandbox worker pool. Valid attempts are packaged under
`grok-trials/`, including their full trajectory, Harbor result, parsed verifier
output, and raw verifier stdout. `grok_trials.json` is the compact per-attempt
index. A solving trajectory is selected when one exists; otherwise the closest
graded attempt is copied into `trajectories-matrix/` and `trajectories/`.

The comparison cohort contains ten verifier-valid Claude Opus 5 OpenCode
attempts per task in the same Daytona snapshots. Each cell combines the
original OpenRouter attempt with independently graded Bedrock global-route
attempts; only runs with complete hidden-verifier verdicts enter n. The 80
attempts are indexed in `opus5_trials.json` and packaged under
`frontier-trials/opus5/`.

### Enterprise long-horizon track: three tasks

These three anonymized tasks do not plant synthetic defects. Each starts from a
pre-feature production revision and asks the agent to implement a real feature
or migration across multiple coupled subsystems. Independently authored hidden
tests grade the behavioral contract; the authorized production change serves
only as a solvability oracle. This track measures requirement retention,
state-machine composition, and cross-boundary implementation over a longer
dependency chain.

Each task received eight independent Grok 4.5 attempts and eight independent
Claude Opus 5 attempts through OpenCode 1.18.13. Only runs matching the frozen
task checksum, exact route, isolated Daytona environment, single-agent policy,
and complete hidden-verifier output enter the denominator. The 48 accepted
attempts are indexed in `long-horizon-enterprise-results.json` and packaged
under `long-horizon-enterprise-trials/`.

### Separate native-table difficulty control

`long-native-table-migration` is also a production-derived feature migration,
but it remains separate from the three-task capability-gap cohort. Opus 5,
Grok 4.5, and GPT-5.6 Sol each scored 0/3, so it establishes shared frontier
difficulty rather than a Grok-specific gap.

## Headline result

### Enterprise long-horizon tasks

The strongest capability separation appears on the three new long-horizon
tasks. Across 29 required behavioral checks, Grok solves **0/24** attempts while
Opus solves **19/24**.

Using the unbiased estimator `1 − C(n−c, k) / C(n, k)`, the largest supported
`k` is 8 because each task/model cell has eight valid attempts:

| Task | Required checks | Model | c/n | pass@1 | pass@3 | pass@8 |
|---|---:|---|---:|---:|---:|---:|
| Customer billing-schedule migration | 8 | Grok 4.5 | 0/8 | 0.0000 | 0.0000 | 0.0000 |
| Customer billing-schedule migration | 8 | Claude Opus 5 | 7/8 | 0.8750 | 1.0000 | 1.0000 |
| Top-up billing lifecycle | 11 | Grok 4.5 | 0/8 | 0.0000 | 0.0000 | 0.0000 |
| Top-up billing lifecycle | 11 | Claude Opus 5 | 7/8 | 0.8750 | 1.0000 | 1.0000 |
| S3 datastore measurement | 10 | Grok 4.5 | 0/8 | 0.0000 | 0.0000 | 0.0000 |
| S3 datastore measurement | 10 | Claude Opus 5 | 5/8 | 0.6250 | 0.9821 | 1.0000 |
| **Macro mean** | N/A | **Grok 4.5** | **0/24** | **0.0000** | **0.0000** | **0.0000** |
| **Macro mean** | N/A | **Claude Opus 5** | **19/24** | **0.7917** | **0.9940** | **1.0000** |

The summary c/n values are sums across task cells; the pass@k summary is the
unweighted macro mean of the three task-level estimators, not a pooled
24-attempt estimator. At n=8, pass@8 is task coverage: it is 1 for any cell
with at least one solve and 0 for a zero-solve cell.

### Bug-injection debugging tasks

On the eight latent-defect debugging tasks, Grok solved **21/80 attempts** for
a macro mean **pass@1 of 0.2625**, **pass@3 of 0.3833**, and **pass@10 of
0.5000**. Its task-level result is:

| Task | c/n | pass@1 | pass@3 | pass@10 |
|---|---:|---:|---:|---:|
| credit-normalize | 8/10 | 0.800 | 1.000 | 1.000 |
| doc-extractors | 0/10 | 0.000 | 0.000 | 0.000 |
| financial-tools | 0/10 | 0.000 | 0.000 | 0.000 |
| phone-invites | 9/10 | 0.900 | 1.000 | 1.000 |
| fiu | 2/10 | 0.200 | 0.533 | 1.000 |
| txenrich | 2/10 | 0.200 | 0.533 | 1.000 |
| txenrich3 | 0/10 | 0.000 | 0.000 | 0.000 |
| txenrich4 | 0/10 | 0.000 | 0.000 | 0.000 |

The apparent tension between the three means is the main Grok result. Grok's
solves are concentrated in four tasks, while GPT-5.6 Sol solves fewer attempts
overall but covers six tasks. The completed August frontier screen adds a new
leader: Opus 5 is both more repeatable and more broadly capable than either.

| OpenCode model | Solves | Mean pass@1 | Mean pass@3 | Mean pass@10 | Tasks with a solve |
|---|---:|---:|---:|---:|---:|
| **Claude Opus 5** | **55/80** | **0.688** | **0.834** | **0.875** | **7/8** |
| **Grok 4.5** | **21/80** | **0.263** | 0.383 | 0.500 | 4/8 |
| GPT-5.6 Sol | 16/80 | 0.200 | **0.435** | **0.750** | **6/8** |
| Claude Opus 4.8 | 8/79 | 0.100 | 0.244 | 0.375 | 3/8 |
| Nova Premier | 0/80 | 0.000 | 0.000 | 0.000 | 0/8 |

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
whether Opus 5 fails at least half of its independent valid attempts.
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

### Pass@k results

Using the unbiased estimator `1 − C(n−c, k) / C(n, k)`, the largest supported
`k` is 8 because each task/model cell has eight valid attempts:

| Task | Required checks | Model | c/n | pass@1 | pass@3 | pass@8 |
|---|---:|---|---:|---:|---:|---:|
| Customer billing-schedule migration | 8 | Grok 4.5 | 0/8 | 0.0000 | 0.0000 | 0.0000 |
| Customer billing-schedule migration | 8 | Claude Opus 5 | 7/8 | 0.8750 | 1.0000 | 1.0000 |
| Top-up billing lifecycle | 11 | Grok 4.5 | 0/8 | 0.0000 | 0.0000 | 0.0000 |
| Top-up billing lifecycle | 11 | Claude Opus 5 | 7/8 | 0.8750 | 1.0000 | 1.0000 |
| S3 datastore measurement | 10 | Grok 4.5 | 0/8 | 0.0000 | 0.0000 | 0.0000 |
| S3 datastore measurement | 10 | Claude Opus 5 | 5/8 | 0.6250 | 0.9821 | 1.0000 |
| **Macro mean** | N/A | **Grok 4.5** | **0/24** | **0.0000** | **0.0000** | **0.0000** |
| **Macro mean** | N/A | **Claude Opus 5** | **19/24** | **0.7917** | **0.9940** | **1.0000** |

The summary c/n values are sums across task cells; the pass@k summary is the
unweighted macro mean of the three task-level estimators, not a pooled
24-attempt estimator. At n=8, pass@8 is task coverage: it is 1 for any cell
with at least one solve and 0 for a zero-solve cell.

### Measured effort

Agent wall time excludes sandbox setup and grading. Trial wall time includes
those phases and remote scheduling/provider latency.

| Model | Task | Turns, mean | Tool calls, mean | Agent time, median (range) | Trial time, range |
|---|---|---:|---:|---:|---:|
| Grok | Billing | 17.3 | 64.4 | 2.9m (2.8–3.7m) | 3.3m–25.3m |
| Opus | Billing | 62.3 | 67.1 | 10.5m (7.9–12.2m) | 8.7m–22.8m |
| Grok | Top-up | 54.6 | 161.4 | 13.6m (10.6–19.2m) | 12.0m–58.6m |
| Opus | Top-up | 149.9 | 149.6 | 27.5m (21.6–40.2m) | 22.2m–59.7m |
| Grok | S3 | 22.1 | 74.0 | 5.7m (5.2–18.4m) | 5.8m–18.9m |
| Opus | S3 | 109.0 | 111.5 | 25.1m (19.7–36.3m) | 20.3m–37.6m |

Across the 48 valid attempts, the agents produced 3,321 model turns and 5,024
tool calls. Top-up produces the deepest measured trajectories. Billing is
structurally long-horizon even though Grok converges quickly, because all eight
runs reach the same nearly complete but behaviorally incorrect implementation.

### Grok win conditions on enterprise long-horizon tasks

Grok records no binary win in this cohort, so "win conditions" here means the
conditions under which it reaches a high fraction of the required hidden
checks. The closest Grok attempt on each task is compared with the first Opus
solve:

| Task | Best Grok checks | Opus comparison | What Grok completed | Remaining gate |
|---|---:|---:|---|---|
| Billing schedule | 7/8 | 7/8 attempts solve | customer create/update flow, invoice range and ledger, queue routing, empty usage | preserve one nested identity field on schedule replacement |
| Top-up lifecycle | 9/11 | 7/8 attempts solve | DTO/entity persistence, threshold arithmetic, gap charging, credit storage, hourly usage deduction | unify validation and scheduler identity across every lifecycle entry point |
| S3 measurement | 8/10 | 5/8 attempts solve | IAM trust/update, persistence, connector ingestion, mirrored DLQ behavior | return one exact canonical location shape through setup, persistence, and create |

The positive pattern is competent repository mapping plus correct local
implementation when the prompt names a boundary and gives an exact data-flow
rule. For example, the [best Grok top-up trace](long-horizon-enterprise-trials/grok45/paigo-top-up-billing-lifecycle/attempt-08/trajectory.json)
implements the core refill calculation and payment mode directly:

```ts
const unitCost = Math.round((topUpAmount - currentBalance) * 100) / 100;
lineItems.addLineItem(new InvoiceLineItem(`${this.offeringName} - Top Up`, 1, unitCost));
await this.invoicesService.create({
    businessID: this.businessID,
    customer,
    customerId: customer.customerId,
    items: lineItems,
    invoiceDate: new Date().toISOString(),
    currency: Offering.getCurrency({ customer, offering: this }),
    storePaymentAsCredit: true,
});
```

That attempt passes the charging, credit-storage, threshold, persistence, and
hourly wallet checks. Billing is even more repeatable: every Grok attempt passes
7/8. S3 shows breadth across AWS and application code, with the closest attempt
passing 8/10. Grok comes closest when each requirement can be closed with a
named local edit and a direct replay. It falls short when the same invariant
must remain exact across several constructors, lifecycle paths, or serialized
representations.

### Failure modes and model contrast

The selected pairs below compare Grok's closest graded attempt with a complete
Opus 5 solve. Each example links the full trajectory and the Grok verifier
output; the code is copied from the recorded tool calls, not reconstructed from
the oracle.

#### Billing: declared invariant, omitted nested field

[Grok attempt 1](long-horizon-enterprise-trials/grok45/paigo-customer-billing-schedule-migration/attempt-01/trajectory.json)
passes 7/8, while [Opus attempt 2](long-horizon-enterprise-trials/opus5/paigo-customer-billing-schedule-migration/attempt-02/trajectory.json)
passes 8/8. In step 13, Grok correctly preserves `subject` and `businessID` at
the scheduler's top level but omits `businessID` from the nested parameters:

```ts
// Grok
scheduleParameters: { customerId },
subject,
businessID,

// Opus
scheduleParameters: { customerId, businessID },
subject,
businessID,
```

The [verifier output](long-horizon-enterprise-trials/grok45/paigo-customer-billing-schedule-migration/attempt-01/verifier-test-stdout.txt)
shows that exact object mismatch. Grok's final step nevertheless says
"`subject` + `businessID` preserved," so the failure is not missing task
comprehension. It is a final-diff verification failure: the summary tracks the
intended invariant rather than the object actually written. Opus reduces the
surface by routing create and replacement through one billing-schedule helper.

**Where to improve:** maintain a field-level contract ledger for every outbound
object, then inspect or test the final object at each creation site before
declaring completion. A targeted assertion on both the top-level scheduler and
its nested `scheduleParameters` would have converted all eight Grok near misses.

#### Top-up: parallel implementations instead of one lifecycle invariant

[Grok attempt 8](long-horizon-enterprise-trials/grok45/paigo-top-up-billing-lifecycle/attempt-08/trajectory.json)
passes 9/11, while [Opus attempt 1](long-horizon-enterprise-trials/opus5/paigo-top-up-billing-lifecycle/attempt-01/trajectory.json)
passes 11/11. Grok implements most of the wallet state machine, but its top-up
enrollment returns before the shared schedule-registration path:

```ts
// Grok
if (this.billingCycle === ValidBillingCycles.topUp) {
    if (customer) await this.topUp({ customer });
    return;
}
await this.registerBillingSchedule(subject);
```

It creates a second scheduler path in `OfferingService`, leaving the domain
registration path customer-specific. The [verifier output](long-horizon-enterprise-trials/grok45/paigo-top-up-billing-lifecycle/attempt-08/verifier-test-stdout.txt)
therefore observes `customer-1` and `customer-2` as different scheduler IDs.
Opus instead changes the shared lifecycle boundary:

```ts
// Opus
if (this.isTopUp()) {
    await this.registerTopUpSchedule(subject);
    return;
}
```

Its schedule helper then fixes identity at offering scope:

```ts
static getTopUpSchedulerID(offeringId: string): string {
    return offeringId;
}
```

The other failed check has the same shape. Grok places non-top-up field
rejection inline in one service path; the verifier finds no reusable
`validateTopUpFields` boundary. Opus extracts that validator and calls it from
both create and update. The gap is state-machine composition, not the refill
math: Grok implements correct pieces in parallel paths, while Opus makes the
invariant authoritative at the shared boundary.

**Where to improve:** identify the lowest shared lifecycle boundary before
editing, centralize each invariant there, and test it through at least two
entry points. For this task, a two-customer scheduler test plus create/update
validation tests would expose both residual failures before grading.

#### S3: correct architecture, non-canonical output string

[Grok attempt 1](long-horizon-enterprise-trials/grok45/paigo-s3-datastore-measurement/attempt-01/trajectory.json)
passes 8/10, while [Opus attempt 1](long-horizon-enterprise-trials/opus5/paigo-s3-datastore-measurement/attempt-01/trajectory.json)
passes 10/10. Grok provisions the IAM role, preserves trust identity, persists
the generated fields, ingests valid records, and mirrors malformed records. Its
two failures share one string-format decision:

```ts
// Grok
dbAccessInformation.ingestion = `s3://${ingestionBucket}/${businessID}/`;
dbAccessInformation.dlq = `s3://${dlqBucket}/${businessID}/`;

// Opus
public static ingestionLocation(businessID: string) {
    return `s3://${process.env.DB_MEASUREMENT_BUCKET_NAME}/${businessID}`;
}
public static dlqLocation(businessID: string) {
    return `s3://${process.env.DB_MEASUREMENT_DLQ_BUCKET_NAME}/${businessID}`;
}
```

The [verifier output](long-horizon-enterprise-trials/grok45/paigo-s3-datastore-measurement/attempt-01/verifier-test-stdout.txt)
shows the received trailing slash against the required no-slash location in
both `setupAccess` and create-persist-return checks. One non-canonical value
therefore closes two otherwise correct cross-boundary paths. Opus defines one
location helper and reuses its exact result through provisioning, persistence,
and response construction.

**Where to improve:** treat returned identifiers and locations as exact API
types, not presentation strings. Build one canonical constructor and add strict
equality checks at setup, persistence round-trip, and API return boundaries.

Across the three pairs, the separating capability is final contract closure.
Grok's closest attempts are substantial and usually build, but their final
summaries stop at plausible feature completeness. The successful Opus traces
more often centralize the invariant, retain an explicit task checklist, and
exercise the final boundary object. The most direct training target is therefore
not more repository exploration; it is repeated prompt-to-diff reconciliation,
shared-boundary selection, and exact final-state verification.

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

## Bug-injection debugging analysis

### Bug-task pass@k results

Each model/task cell has ten verifier-valid attempts. Using the unbiased
estimator `1 − C(n−c, k) / C(n, k)`, the task-level comparison is:

| Task | Required checks | Model | c/n | pass@1 | pass@3 | pass@10 |
|---|---:|---|---:|---:|---:|---:|
| credit-normalize | 19 | Grok 4.5 | 8/10 | 0.8000 | 1.0000 | 1.0000 |
| credit-normalize | 19 | Claude Opus 5 | 8/10 | 0.8000 | 1.0000 | 1.0000 |
| doc-extractors | 19 | Grok 4.5 | 0/10 | 0.0000 | 0.0000 | 0.0000 |
| doc-extractors | 19 | Claude Opus 5 | 6/10 | 0.6000 | 0.9667 | 1.0000 |
| financial-tools | 23 | Grok 4.5 | 0/10 | 0.0000 | 0.0000 | 0.0000 |
| financial-tools | 23 | Claude Opus 5 | 3/10 | 0.3000 | 0.7083 | 1.0000 |
| phone-invites | 17 | Grok 4.5 | 9/10 | 0.9000 | 1.0000 | 1.0000 |
| phone-invites | 17 | Claude Opus 5 | 9/10 | 0.9000 | 1.0000 | 1.0000 |
| FIU | 19 | Grok 4.5 | 2/10 | 0.2000 | 0.5333 | 1.0000 |
| FIU | 19 | Claude Opus 5 | 10/10 | 1.0000 | 1.0000 | 1.0000 |
| txenrich | 17 | Grok 4.5 | 2/10 | 0.2000 | 0.5333 | 1.0000 |
| txenrich | 17 | Claude Opus 5 | 9/10 | 0.9000 | 1.0000 | 1.0000 |
| txenrich3 | 19 | Grok 4.5 | 0/10 | 0.0000 | 0.0000 | 0.0000 |
| txenrich3 | 19 | Claude Opus 5 | 10/10 | 1.0000 | 1.0000 | 1.0000 |
| txenrich4 | 19 | Grok 4.5 | 0/10 | 0.0000 | 0.0000 | 0.0000 |
| txenrich4 | 19 | Claude Opus 5 | 0/10 | 0.0000 | 0.0000 | 0.0000 |
| **Macro mean** | N/A | **Grok 4.5** | **21/80** | **0.2625** | **0.3833** | **0.5000** |
| **Macro mean** | N/A | **Claude Opus 5** | **55/80** | **0.6875** | **0.8344** | **0.8750** |

The summary c/n values are sums across task cells; pass@k is the unweighted
macro mean of the eight task-level estimators. At n=10, pass@10 is task
coverage. The comparison therefore shows both a repeatability gap, 21/80
versus 55/80, and a breadth gap, four of eight tasks with a Grok solve versus
seven of eight with an Opus solve.

### Bug-task measured effort

A model turn is an agent-sourced OpenCode trajectory step and records one LLM
call. Full trial wall time is Harbor `started_at` to `finished_at`, including
environment setup, agent setup, execution, and verification.

| Model | Valid trials | Model turns | Tool calls | Mean trial wall time | Median | p90 | Range |
|---|---:|---:|---:|---:|---:|---:|---:|
| Grok 4.5 | 80 | 967 | 2,521 | 4m 27.9s | 3m 52.0s | 8m 33.5s | 1m 28.5s-15m 14.5s |
| Claude Opus 5 | 80 | 3,061 | 3,316 | 12m 46.1s | 10m 14.5s | 23m 28.3s | 5m 04.3s-30m 28.0s |

| Model | Task | Turns, mean | Tool calls, mean | Trial wall time, mean | Trial wall time, range |
|---|---|---:|---:|---:|---:|
| Grok | credit-normalize | 10.9 | 22.3 | 3.12m | 2.48-3.95m |
| Opus | credit-normalize | 33.0 | 37.5 | 7.48m | 5.18-10.71m |
| Grok | doc-extractors | 9.1 | 19.1 | 1.89m | 1.59-2.39m |
| Opus | doc-extractors | 25.9 | 30.9 | 9.73m | 5.65-23.47m |
| Grok | financial-tools | 8.2 | 21.9 | 1.70m | 1.48-1.85m |
| Opus | financial-tools | 43.9 | 47.4 | 10.30m | 5.07-17.00m |
| Grok | phone-invites | 8.0 | 15.8 | 2.09m | 1.80-2.32m |
| Opus | phone-invites | 17.1 | 18.6 | 8.13m | 7.08-12.71m |
| Grok | FIU | 15.4 | 46.8 | 5.44m | 4.14-7.49m |
| Opus | FIU | 36.2 | 42.9 | 15.26m | 7.44-30.47m |
| Grok | txenrich | 14.2 | 36.4 | 6.77m | 5.51-10.20m |
| Opus | txenrich | 41.7 | 43.2 | 13.23m | 7.03-22.97m |
| Grok | txenrich3 | 14.3 | 43.5 | 4.89m | 3.78-5.82m |
| Opus | txenrich3 | 54.5 | 55.8 | 16.90m | 9.72-27.17m |
| Grok | txenrich4 | 16.6 | 46.3 | 9.81m | 7.53-15.24m |
| Opus | txenrich4 | 53.8 | 55.3 | 21.13m | 10.24-30.21m |

Grok's 80 valid trials ran in a global 12-sandbox pool. The first valid start
to last valid finish was **1h 08m 28.8s**, with peak observed concurrency 12.
The Opus attempts combine the original exact-route OpenRouter screen with
later exact Bedrock-route attempts, so they do not form one comparable
single-wave envelope. Independently running trial durations are not summed.

The Grok phase timestamps put the mean trial at 2.2s of environment setup,
20.5s of agent setup, 234.6s of agent execution, and 6.6s of verification,
with the small remainder in handoffs. Solved Grok attempts were shorter than
unsolved attempts on average, 10.6 versus 12.6 model turns and 3.07m versus
4.96m, but task difficulty confounds that comparison. The same Grok
trajectories report **46,841,681 input tokens**, including **39,586,944 cached
tokens**, and **467,658 output tokens**.

### Grok win conditions on bug-injection tasks

Unlike the enterprise long-horizon cohort, this track contains 21 binary Grok
wins. Those wins are highly concentrated rather than uniformly distributed:

| Task | Grok c/n | Opus c/n | Observed Grok win condition |
|---|---:|---:|---|
| credit-normalize | 8/10 | 8/10 | named normalization helpers, exact string cases, and a local regression surface |
| phone-invites | 9/10 | 9/10 | direct prefix and fallback-order defects in one integration path |
| FIU | 2/10 | 10/10 | every small utility invariant is found across files in the same attempt |
| txenrich | 2/10 | 9/10 | the exact target boundary is changed without widening adjacent bank rules |
| doc-extractors | 0/10 | 6/10 | no Grok attempt preserves both the newly valid boundary and the negative pin |
| financial-tools | 0/10 | 3/10 | no Grok attempt carries the single-late delinquency condition into the final diff |
| txenrich3 | 0/10 | 10/10 | no Grok attempt fixes the mandate sentinel in the bank implementation that owns the failing row |
| txenrich4 | 0/10 | 0/10 | neither model closes all five parser cases in one regression-safe patch |

The positive pattern is fast closure when the symptom maps to one named local
operation. For example, [Grok phone attempt 1](grok-trials/latent-phone-invites/attempt-01/trajectory.json)
fixes the international prefix by consuming both zeroes, then preserves the
configured region by taking the first plausible fallback:

```python
if value.startswith("00"):
    value = "+" + value[2:]

if possible_matches:
    return possible_matches[0]
```

That attempt passes all 17 required checks. The failure pattern begins when a
ticket describes several similar boundaries and success requires selecting
the exact implementation locus plus retaining neighboring negative examples.
In those cases, Grok often makes a semantically plausible edit and stops after
positive-case replay, while Opus more often enumerates the boundary triplet or
executes a wider regression matrix.

### Bug-task failure modes and model contrast

The pairs below compare a closest Grok attempt with a complete Opus solve when
one exists. Each verifier link exposes the exact remaining assertion. The code
comes from recorded edit calls in the linked trajectories.

#### Doc extraction: boundary repair without the negative pin

[Grok attempt 5](grok-trials/latent-doc-extractors/attempt-05/trajectory.json)
passes 18/19 checks, while [Opus attempt 1](frontier-trials/opus5/latent-doc-extractors/attempt-01/trajectory.json)
passes 19/19. Both models recognize that the fallback rent-roll minimum of
three lines is too strict. Grok lowers it to one; Opus lowers it to two and
names the retained invariant:

```python
# Grok
return total if count >= 1 else None

# Opus
_MIN_RENT_ROLL_LINES = 2
return total if count >= _MIN_RENT_ROLL_LINES else None
```

The [Grok verifier output](grok-trials/latent-doc-extractors/attempt-05/verifier-output.json)
shows the consequence: the two-line rent roll now works, but a single stray
rent line is incorrectly accepted. All ten Grok attempts fail that negative
pin. Six Opus attempts solve the task; the other four make the same one-line
over-generalization, so the separation is repeatability at preserving both
sides of a semantic boundary rather than exclusive access to the solution.

**Where to improve:** for every relaxed threshold, generate and replay the
below-boundary, exact-boundary, and above-boundary cases before stopping. A
three-row local table for counts 1, 2, and 3 would have exposed the regression.

#### Financial tools: one ticket condition never reaches the diff

[Grok attempt 1](grok-trials/latent-financial-tools/attempt-01/trajectory.json)
passes 22/23 checks, while [Opus attempt 6](frontier-trials/opus5/latent-financial-tools/attempt-06/trajectory.json)
passes 23/23. Grok repairs five other threshold or sentinel defects but leaves
the severe-delinquency condition unchanged. Opus searches for `late_90` and
makes the required one-character boundary edit:

```python
# Grok final state
if (int(t.get("late_90") or 0) > 1) or bool(t.get("is_chargeoff"))

# Opus
if (int(t.get("late_90") or 0) > 0) or bool(t.get("is_chargeoff"))
```

The [Grok verifier output](grok-trials/latent-financial-tools/attempt-01/verifier-output.json)
shows that zero and two severe lates behave correctly but exactly one does not.
Every Grok attempt leaves this same check failing. Opus solves three of ten;
the remaining seven also miss it, so this is another repeatability gap around
complete ticket-to-diff reconciliation.

**Where to improve:** maintain a case-level checklist whose entries close only
when the corresponding symbol appears in the final diff or a test proves that
no edit is needed. For this case, searching each ticket noun and replaying
`late_90` values 0, 1, and 2 would prevent the silent omission.

#### Txenrich: broad regex expansion instead of one exact width

[Grok attempt 2](grok-trials/xrepo-txenrich-latent/attempt-02/trajectory.json)
passes all five fail-to-pass checks but breaks two pass-to-pass checks. [Opus
attempt 1](frontier-trials/opus5/xrepo-txenrich-latent/attempt-01/trajectory.json)
passes all 17. The planted HDFC defect is a single incorrect length check:

```python
# Opus: exact repair
transactions.remark.str.len().eq(16)
```

Grok instead adds broad rules across HDFC and several sibling banks:

```python
# Grok: accepts any numeric remark from 5 through 16 characters
transactions.remark.str.contains("^[0-9]{5,16}$", na=False, case=False)
```

The [Grok verifier output](grok-trials/xrepo-txenrich-latent/attempt-02/verifier-output.json)
shows both regressions: a 15-character remark becomes a cheque deposit and a
non-zero-prefixed 16-character remark is also accepted. Eight of ten Grok
attempts break the 15-character pin, while Opus solves nine of ten by changing
the one exact width rather than generalizing the parser family.

**Where to improve:** prefer the smallest predicate change consistent with the
symptom, then diff outputs on the target row and its nearest negative siblings.
Do not propagate a regex widening across bank modules without evidence that
each module shares the same contract.

#### Txenrich3: correct symptom family, wrong bank implementation

[Grok attempt 5](grok-trials/xrepo-txenrich3-latent/attempt-05/trajectory.json)
passes 18/19 checks, while [Opus attempt 1](frontier-trials/opus5/xrepo-txenrich3-latent/attempt-01/trajectory.json)
passes 19/19. Grok recognizes the one-rupee mandate pattern, but implements it
in `BankOfMaharashtra.py`. The failing row is dispatched through
`Indusind.py`, where the planted value remains 2. Opus edits that owning rule:

```python
# Grok adds a plausible sibling-bank rule
transactions.amount.eq(1) & transactions.description.str.contains("MANDATE|Mandate")

# Opus fixes the rule reached by the failing row
transactions.amount.eq(2)  # before
transactions.amount.eq(1)  # after
```

The [Grok verifier output](grok-trials/xrepo-txenrich3-latent/attempt-05/verifier-output.json)
still reports the rupee-one mandate failure. All ten Grok attempts miss this
check; Opus solves all ten. Eight Grok attempts also miss the adjacent
six-digit cheque width, which reinforces that the issue is not parser syntax
but exact row-to-handler localization across many near-duplicate bank scripts.

**Where to improve:** replay the reported row through the repository's bank
dispatcher and record the concrete handler before editing. A repository-wide
search should enumerate candidate rules, but runtime ownership should decide
which one receives the patch.

#### Txenrich4: complementary near misses and shared frontier difficulty

Both models score 0/10, so txenrich4 is not evidence of a Grok-specific
capability gap. [Grok attempt 1](grok-trials/xrepo-txenrich4-latent/attempt-01/trajectory.json)
and [Opus attempt 2](frontier-trials/opus5/xrepo-txenrich4-latent/attempt-02/trajectory.json)
each pass 18/19 checks, but they miss different parser cases. Grok closes the
UPI case and leaves the PNB NEFT capture index unchanged; Opus fixes NEFT but
still misses UPI:

```python
# Grok leaves the one-group regex at an out-of-range capture index
py_extract(transactions.description, pat="NEFT (.*)", index=1)

# Opus fixes NEFT extraction
py_extract(transactions.description, pat="NEFT (.*)", index=0)
```

The [Grok verifier output](grok-trials/xrepo-txenrich4-latent/attempt-01/verifier-output.json)
fails only `test_neft_credit_payee_name`; the [Opus verifier output](frontier-trials/opus5/xrepo-txenrich4-latent/attempt-02/verifier-output.json)
fails only `test_upi_credit_payee_name`. Across all ten attempts, Grok misses
NEFT ten times and UPI seven times; Opus misses UPI nine times and NEFT five
times. Both models can repair individual symptoms, but neither reliably keeps
the full five-case parser contract closed in one patch.

**Where to improve:** keep the five reported parser cases as an executable
matrix of final category and payee outputs. Re-run the whole matrix after each
regex-priority or segment-index edit instead of validating only the most recent
case.

Together, the bug tasks isolate a narrower capability gap than the enterprise
cohort. Grok is fast and often reaches 18 of 19 or 22 of 23 checks, but it is
less reliable at preserving negative pins, reconciling every ticket item with
the final diff, and selecting the exact owner among repeated implementations.
The relevant training target is boundary-complete verification: explicit
case ledgers, minimal edits, runtime-path localization, and positive plus
negative replay before completion.

The aggregate indexes and per-attempt evidence are in
[`grok_trials.json`](grok_trials.json), [`opus5_trials.json`](opus5_trials.json),
[`grok-trials/`](grok-trials/), and [`frontier-trials/opus5/`](frontier-trials/opus5/).

## Native-table migration difficulty control

The earlier `long-native-table-migration` study is retained as a shared
difficulty control rather than a Grok-specific capability gap. Its final
comparison contains nine valid attempts, three each for Opus 5, Grok 4.5, and
GPT-5.6 Sol. All three models solved **0/3**, so Opus independently exceeds the
50% difficulty threshold. Tool calls ranged from **80 to 169**, with a
conventional nine-trial median of **116**. Six traces
exceeded the original 70–100 reference band; the checked-in
`long_horizon_results.json` correctly treats that band as descriptive, reports
the difficulty gate as true, and sets overall `qualifies: true`.

The control keeps OpenCode 1.18.13 and the Daytona snapshot fixed. Valid scored
trials use the exact OpenRouter routes for all three models. Zero-turn transport
attempts are excluded as infrastructure failures rather than counted as model
failures.

pass@k uses `1 − C(n−c, k) / C(n, k)`. Every row has `n=3`, `c=0`:

| Model | Solves | pass@1 | pass@2 | pass@3 | Model turns | Tool calls, median (range) | Trial wall time, mean / median (range) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Claude Opus 5 | 0/3 | 0.000 | 0.000 | 0.000 | 437 | 168 (148–169) | 56m 52.7s / 50m 07.4s (41m 46.6s–78m 44.2s) |
| Grok 4.5 | 0/3 | 0.000 | 0.000 | 0.000 | 110 | 116 (108–134) | 11m 41.9s / 11m 09.2s (10m 11.9s–13m 44.7s) |
| GPT-5.6 Sol | 0/3 | 0.000 | 0.000 | 0.000 | 113 | 90 (80–90) | 8m 24.9s / 8m 41.1s (7m 35.9s–8m 57.8s) |

| Model | Attempt | Reward | f2p | p2p | Model turns | Tool calls | Full trial wall time | Input (cached) / output tokens | Grading |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Opus 5 | 1 | 0 | 0/4 | 1/2 | 150 | 169 | 50m 07.4s | 34.89M (34.89M) / 143.9k | regraded final verifier |
| Opus 5 | 2 | 0 | 1/4 | 1/2 | 154 | 168 | 78m 44.2s | 38.24M (38.24M) / 150.7k | regraded final verifier |
| Opus 5 | 3 | 0 | 0/4 | 1/2 | 133 | 148 | 41m 46.6s | 26.20M (26.20M) / 125.0k | regraded final verifier |
| Grok 4.5 | 1 | 0 | 1/4 | 2/2 | 39 | 134 | 11m 09.2s | 2.80M (2.67M) / 32.7k | original Harbor verifier |
| Grok 4.5 | 2 | 0 | 1/4 | 1/2 | 36 | 116 | 13m 44.7s† | 2.72M (2.52M) / 31.4k | recovered + regraded final verifier |
| Grok 4.5 | 3 | 0 | 1/4 | 2/2 | 35 | 108 | 10m 11.9s | 2.71M (2.50M) / 28.2k | original Harbor verifier |
| GPT-5.6 Sol | 1 | 0 | 1/4 | 1/2 | 37 | 80 | 7m 35.9s | 2.24M (2.24M) / 13.4k | original Harbor verifier |
| GPT-5.6 Sol | 2 | 0 | 1/4 | 1/2 | 40 | 90 | 8m 41.1s | 2.73M (2.73M) / 14.1k | original Harbor verifier |
| GPT-5.6 Sol | 3 | 0 | 1/4 | 1/2 | 36 | 90 | 8m 57.8s | 2.73M (2.73M) / 15.1k | original Harbor verifier |

The comparison used **660 model turns**, **1,103 tool calls**, **115.26M input
tokens** (114.72M cached), and **554.3k output tokens**. Independently running
trial durations are not summed.

† Eight durations are full Harbor `started_at`→`finished_at` wall time,
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
scores 1. All three Opus candidate worktrees then executed the final six-test
suite and remained reward 0; the Grok and Sol trials ran only after
that verifier was frozen. Regrade provenance is explicit in every packaged
trial index, and the prompt-to-test audit is preserved under
`long-horizon-controls/fairness-audit.md`.

## Caveats

- The bug-injection pass and effort comparison covers 80 valid Grok attempts
  and 80 valid Opus attempts. Its phase, token, concurrency, and single-wave
  envelope measurements are explicitly limited to Grok's 80 attempts. The
  enterprise effort table covers its separate 48-attempt Grok/Opus cohort.
  Infrastructure/auth failures are excluded from all scores and valid-trial
  totals.
- Ten attempts per bug-injection task and eight per enterprise task expose
  systematic zero rows and strong concentration, but each individual solve
  rate still has binomial uncertainty.
- `pass@10` is 1 for any n=10 cell with at least one solve and 0 otherwise. Its
  macro mean is therefore task coverage at this sample size, not an additional
  measure of within-task repeatability. The same interpretation applies to
  `pass@8` in the enterprise cohort.
- Hidden tests assert behavior, not oracle patch identity. Alternative correct
  implementations pass; the failures above are observable output failures, not
  textual-diff mismatches.
