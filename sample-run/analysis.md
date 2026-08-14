# Analyzing Grok 4.5 Behaviour on Long Horizon and Enterprise Coding Tasks

## Table of contents

- [Setup](#setup)
- [Headline result](#headline-result)
  - [Enterprise long-horizon tasks](#enterprise-long-horizon-tasks)
  - [Bug-injection debugging tasks](#bug-injection-debugging-tasks)
- [What the traces show](#what-the-traces-show)
- [Long-horizon capability-gap results](#long-horizon-capability-gap-results)
  - [Pass@k results](#passk-results)
  - [Measured effort](#measured-effort)
  - [Grok win conditions on enterprise long-horizon tasks](#grok-win-conditions-on-enterprise-long-horizon-tasks)
  - [Failure modes and model contrast](#failure-modes-and-model-contrast)
    - [What was different in the reasoning](#what-was-different-in-the-reasoning)
    - [Billing: said the field was preserved without checking the final object](#billing-said-the-field-was-preserved-without-checking-the-final-object)
    - [Top-up: connected the wallet through the wrong service](#top-up-connected-the-wallet-through-the-wrong-service)
    - [S3: built the pieces but did not verify the full data path](#s3-built-the-pieces-but-did-not-verify-the-full-data-path)
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
  - [Native-table measured effort](#native-table-measured-effort)
  - [Native-table verifier contract](#native-table-verifier-contract)
  - [Native-table trace analysis](#native-table-trace-analysis)
    - [Grok: compile success masked an unusable native result](#grok-compile-success-masked-an-unusable-native-result)
    - [GPT-5.6 Sol: policy labels without policy-specific behavior](#gpt-56-sol-policy-labels-without-policy-specific-behavior)
    - [Opus 5: broad implementation, broken integration seam](#opus-5-broad-implementation-broken-integration-seam)
  - [General takeaway from the control](#general-takeaway-from-the-control)
- [Nature of the source codebases](#nature-of-the-source-codebases)
- [Conclusion](#conclusion)
- [Appendix](#appendix)
  - [Long-horizon definition and evaluation bar](#long-horizon-definition-and-evaluation-bar)

## Setup

This report keeps two evaluation tracks and one difficulty control separate.
The bug-injection track evaluates eight production-derived tasks with ten valid
OpenCode attempts per task for both Grok 4.5 and Claude Opus 5; the enterprise
track evaluates three authentic historical features or migrations with eight
valid attempts per model. Only runs matching the required route, snapshot,
checksum, single-agent policy, and complete hidden-verifier output enter the
denominators. The native-table migration remains a separate three-attempt
control because Opus 5, Grok 4.5, and GPT-5.6 Sol all scored zero, so it cannot
support a model-specific capability claim.

## Headline result

Across three production-derived enterprise tasks, Grok 4.5 solved **0/24**
attempts while Claude Opus 5 solved **19/24**. The clearest behavior comparison
comes from the top-up and S3 tasks, where Grok solved **0/16** attempts and Opus
solved **12/16**. Grok often built most of the feature but missed one or two
connections needed to carry a rule or generated value through the full
workflow.

The billing result remains in the score table, but it is not used to explain
Grok's behavior because one check expects a field placement that the prompt
does not require. The bug-injection results, Grok **21/80** and Opus **55/80**,
are also reported as outcomes rather than used for the main capability claim
because some tasks intentionally hid exact boundary values during calibration.

### Enterprise long-horizon tasks

The headline table uses the unbiased estimator `1 − C(n−c, k) / C(n, k)`.
It reports the unweighted macro mean across the three task cells:

| Task | Required checks | Model | Solves (c/n) | pass@1 | pass@3 | pass@8 |
|---|---:|---|---:|---:|---:|---:|
| **Macro mean** | **29 total** | **Grok 4.5** | **0/24** | **0.0000** | **0.0000** | **0.0000** |
| **Macro mean** | **29 total** | **Claude Opus 5** | **19/24** | **0.7917** | **0.9940** | **1.0000** |

The solves column sums the three task cells. pass@8 is the task-coverage
criterion: 1 when a model solves a task at least once across its eight attempts
and 0 otherwise.

### Bug-injection debugging tasks

The headline uses the same schema and four-decimal precision as the enterprise
table. Each model has ten valid attempts on each of eight tasks:

| Task | Required checks | Model | Solves (c/n) | pass@1 | pass@3 | pass@10 |
|---|---:|---|---:|---:|---:|---:|
| **Macro mean** | **152 total** | **Grok 4.5** | **21/80** | **0.2625** | **0.3833** | **0.5000** |
| **Macro mean** | **152 total** | **Claude Opus 5** | **55/80** | **0.6875** | **0.8344** | **0.8750** |

The solves column sums the eight task cells. pass@10 is the task-coverage
measure because each cell has ten attempts.

## What the traces show

**Main finding.** On the top-up and S3 tasks, Grok usually found the right files
and built much of the requested feature. It failed when one rule or value had
to survive every step of the workflow. Opus completed that handoff more
reliably, solving **12/16** attempts while Grok solved **0/16**.

We compared the final code, tests, commands, and checker results from all 16
Grok runs on these two tasks with the matching Opus runs. Model comments are
used only to compare what the model claimed with what the finished code did.
The code below comes directly from edits recorded in the paired trajectories.

### 1. Grok applied the top-up rules in some places, but not all

The [best Grok run](enterprise-long-horizon-trials/grok45/enterprise-top-up-billing-lifecycle/attempt-08/trajectory.json)
passed 9/11 checks. The
[matching Opus run](enterprise-long-horizon-trials/opus5/enterprise-top-up-billing-lifecycle/attempt-01/trajectory.json)
passed 11/11. Grok still allowed top-up fields in invalid billing modes and did
not create one stable hourly job for each offering.

The task says top-up fields are valid only for top-up billing, subscriptions
cannot use them, and each offering should own one hourly job. Grok added the
rule to some request fields, but not every create and update path. Its final
message still said the invalid fields were rejected and the hourly job was
offering-level. The checker showed otherwise. The hourly-job check failed in
8/8 Grok runs, rejection on other billing modes failed in 7/8, and the combined
usage-based/subscription rule failed in 6/8.

The recorded Grok edit attached the rule to one optional request field:

```ts
@IsEnum(ValidBillingCycles)
@IsOptional()
@Validate(TopUpBillingCycleRule)
@ApiProperty({ enum: ValidBillingCycles, default: ValidBillingCycles.monthly })
public billingCycle?: ValidBillingCycles;
```

Opus put the same validation in the shared create and update paths and based the
job identity on the offering. The important difference is not the exact helper
name. The rule ran wherever data entered the system and was checked again
through the scheduled path.

The paired Opus edit validates creation and the merged update state, then gives
the hourly job an offering-level identity:

```ts
OfferingService.validateTopUpFields(createOfferingDTO);

OfferingService.validateTopUpFields({
    billingCycle: updatedFields?.billingCycle ? updatedFields?.billingCycle : rest?.billingCycle,
    offeringType: updatedFields?.offeringType ? updatedFields?.offeringType : rest?.offeringType,
    topUpAmount: updatedFields?.topUpAmount ? updatedFields?.topUpAmount : rest?.topUpAmount,
    topUpThreshold: updatedFields?.topUpThreshold ? updatedFields?.topUpThreshold : rest?.topUpThreshold,
});

schedulerID: Offering.getTopUpSchedulerID(this.offeringId),
scheduleParameters: {
    businessID: this.businessID,
    offeringId: this.offeringId,
},
```

**What to train:** for every rule written as “when,” “only if,” or “otherwise,”
list each allowed and rejected case. Test the list through create, update, and
scheduled execution before marking the requirement complete.

### 2. Grok created the S3 values, but lost them before they could be used

[Grok attempt 5](enterprise-long-horizon-trials/grok45/enterprise-s3-datastore-measurement/attempt-05/trajectory.json)
passed 5/10 checks. The
[matching Opus run](enterprise-long-horizon-trials/opus5/enterprise-s3-datastore-measurement/attempt-01/trajectory.json)
passed 10/10. Every Grok run failed to return the generated access details and
failed to carry them through creation and storage. Six of eight also failed the
bad-record path.

The task says the generated IAM role, external ID, ingestion location,
dead-letter location, and region must be returned and saved. In attempt 5,
Grok's helper filled in a local object but ended without returning it. The
values existed briefly inside the helper, but the rest of the system could not
save or use them. Opus returned the configured object, saved it, and returned
the created entity from the service.

The recorded Grok edit creates the values but reaches the end of the `try`
block without returning the object:

```ts
dbAccessInformation.platform = SupportedDatastores.s3;
dbAccessInformation.region = region;
dbAccessInformation.externalId = externalId;
dbAccessInformation.iamRoleArn = createRoleResponse.Role?.Arn;
dbAccessInformation.ingestion = ingestion;
dbAccessInformation.dlq = dlq;
} catch (e) {
```

The paired Opus edit returns the same object after filling every generated
field:

```ts
dbAccessInformation.iamRoleArn = Role?.Arn
    ? Role.Arn
    : DatastoreAccessInformation.fallbackRoleArn(roleName);
dbAccessInformation.externalId = externalId;
dbAccessInformation.ingestion = DatastoreAccessInformation.ingestionLocation(businessID);
dbAccessInformation.dlq = DatastoreAccessInformation.dlqLocation(businessID);
dbAccessInformation.region = dbAccessInformation.region
    ? dbAccessInformation.region
    : DatastoreAccessInformation.defaultRegion();

return dbAccessInformation;
```

**What to train:** follow each generated value through four questions. Was it
created? Was it returned? Was it saved? Did the final service return the same
value? Run this check for both the normal path and the bad-record path.

### 3. Grok tested pieces of the feature, then reported the whole job complete

In the top-up run, Grok's final message said validation and hourly-job identity
were complete. Its tests showed that a service could be constructed, but did
not create invalid offerings or inspect the scheduled job. In the S3 run, Grok
said setup, storage, and dead-letter delivery worked after running tests that
never checked the object returned by the setup helper.

Across these 16 runs, Grok ran a build or test after its final source change in
9 cases; Opus did so in all 16. Grok reviewed its final repository changes in
2 cases; Opus did so in 14. These habits do not cause success by themselves,
but the paired examples show what the missing final check would have caught.

**What to train:** before reporting completion, run one test through the same
entry point a real caller uses. Match every sentence in the final summary to a
passing test or an inspected final object. If either is missing, report the open
item instead of calling the task complete.

Taken together, the traces show a narrow and practical weakness. Grok can build
the individual pieces, but it is less reliable at connecting those pieces
across the whole workflow and proving that the final result matches the request.

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

Using the unbiased estimator `1 − C(n−c, k) / C(n, k)`, each task/model cell
has eight valid attempts. The coverage column is therefore pass@8:

| Task | Required checks | Model | Solves (c/n) | pass@1 | pass@3 | pass@8 |
|---|---:|---|---:|---:|---:|---:|
| Customer billing-schedule migration | 8 | Grok 4.5 | 0/8 | 0.0000 | 0.0000 | 0.0000 |
| Customer billing-schedule migration | 8 | Claude Opus 5 | 7/8 | 0.8750 | 1.0000 | 1.0000 |
| Top-up billing lifecycle | 11 | Grok 4.5 | 0/8 | 0.0000 | 0.0000 | 0.0000 |
| Top-up billing lifecycle | 11 | Claude Opus 5 | 7/8 | 0.8750 | 1.0000 | 1.0000 |
| S3 datastore measurement | 10 | Grok 4.5 | 0/8 | 0.0000 | 0.0000 | 0.0000 |
| S3 datastore measurement | 10 | Claude Opus 5 | 5/8 | 0.6250 | 0.9821 | 1.0000 |
| **Macro mean** | **29 total** | **Grok 4.5** | **0/24** | **0.0000** | **0.0000** | **0.0000** |
| **Macro mean** | **29 total** | **Claude Opus 5** | **19/24** | **0.7917** | **0.9940** | **1.0000** |

The summary solve values are sums across task cells; the pass@k summary is the
unweighted macro mean of the three task-level estimators, not a pooled
24-attempt estimator. pass@8 is 1 for any task cell with at least one solve and
0 for a zero-solve cell.

#### Interval estimates

Each cell holds eight attempts, so the per-task rates carry wide intervals.
Wilson 95% intervals for the scored cohort:

| Task | Grok 4.5 | Grok 95% CI | Claude Opus 5 | Opus 95% CI |
|---|---:|---|---:|---|
| Customer billing-schedule migration | 0/8 | [0.000, 0.324] | 7/8 | [0.529, 0.978] |
| Top-up billing lifecycle | 0/8 | [0.000, 0.324] | 7/8 | [0.529, 0.978] |
| S3 datastore measurement | 0/8 | [0.000, 0.324] | 5/8 | [0.306, 0.863] |
| **Pooled** | **0/24** | **[0.0000, 0.1380]** | **19/24** | **[0.5953, 0.9076]** |

The pooled contrast is strong: 0/24 against 19/24 is Fisher exact
p = 7.4e-9, and the intervals do not overlap. Individual task cells are
weaker. The single strongest task-level contrast, S3 at 0/8 against 5/8, is
Fisher exact p = 0.026, which does not survive Bonferroni correction across
three tasks. Per-task rates should therefore be read as directional evidence
about which contracts each model closes, and the pooled result as the
measured claim.

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
rule. For example, the [best Grok top-up trace](enterprise-long-horizon-trials/grok45/enterprise-top-up-billing-lifecycle/attempt-08/trajectory.json)
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

The paired [Opus attempt 1 trace](enterprise-long-horizon-trials/opus5/enterprise-top-up-billing-lifecycle/attempt-01/trajectory.json)
passes all 11 checks and provides the complete comparison for the same task.
The Grok attempt passes the charging, credit-storage, threshold, persistence,
and hourly wallet checks. Billing is even more repeatable: every Grok attempt
passes 7/8. S3 shows breadth across AWS and application code, with the closest
attempt passing 8/10. Grok comes closest when each requirement can be closed
with a named local edit and a direct replay. It falls short when the same invariant
must remain exact across several constructors, lifecycle paths, or serialized
representations.

### Failure modes and model contrast

This section preserves the detailed trace record for all three enterprise
tasks. Only the top-up and S3 examples support the model-specific finding above.
The billing example is kept as a score and verification case, not as evidence
of a Grok capability gap, because one checker expectation was not stated in the
prompt.

The examples below were selected because their verifier output makes the root
cause visible. They are not isolated score differences. All eight Grok billing
runs missed the same check, four of eight Grok top-up runs passed only 3/11
checks, and every Grok S3 run missed at least two checks. The code is copied
from recorded tool calls, not reconstructed from the oracle.

#### What was different in the reasoning

The traces show a simple difference. Grok often asked whether it had added all
the requested pieces. Opus more often asked whether the pieces were connected
correctly and the final system obeyed every rule.

| Reasoning step | Grok 4.5 pattern | Claude Opus 5 pattern |
|---|---|---|
| Choose where a rule belongs | Reuse the nearest object or service that already has related data | Find the object that owns the rule and trace every way it is constructed or called |
| Make the change | Batch many related edits into a small number of turns | Make smaller changes and reason between them |
| Check the result | Rely heavily on build success and existing tests | Add or run boundary-focused tests, then compare the final diff with the task |
| Decide it is done | Summarize intended behavior | Reconcile the request, implementation, tests, and final repository state |

This is visible in the run shape. Across the 24 enterprise attempts, Opus used
2,569 model turns and 2,626 tool calls; Grok used 752 turns and 2,398 tool
calls. Opus therefore used about 3.4 times as many reasoning turns with only
about 9% more tool calls. It paused to interpret results more often instead of
packing several actions into each turn. Opus inspected `git diff` or
`git status` after editing in 24/24 attempts; Grok did so in 2/24. That final
review is evidence of the broader habit, not the whole explanation.

There is no trace evidence that Opus changed its context-window size. It simply
used more of the available run: the mean final-call prompt was about 195k tokens
for Opus and 102k for Grok. That let Opus carry more code, test output, and prior
decisions into its final checks. These counts do not prove that longer traces
cause better results, but they match the task-level failures below.

#### Billing: said the field was preserved without checking the final object

[Grok attempt 1](enterprise-long-horizon-trials/grok45/enterprise-customer-billing-schedule-migration/attempt-01/trajectory.json)
passes 7/8, while [Opus attempt 2](enterprise-long-horizon-trials/opus5/enterprise-customer-billing-schedule-migration/attempt-02/trajectory.json)
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

The [verifier output](enterprise-long-horizon-trials/grok45/enterprise-customer-billing-schedule-migration/attempt-01/verifier-test-stdout.txt)
shows that exact object mismatch. Grok's final step nevertheless says
"`subject` + `businessID` preserved," so the failure is not missing task
comprehension. Grok remembered the rule but checked its intention, not the final
object. Opus reduced the number of places that could drift by routing create and
replacement through one billing-schedule helper, then inspecting the completed
change. The same one-field miss appeared in all eight Grok attempts.

**Where to improve:** keep a short list of every required field, then compare
that list with the actual final object before declaring completion. A test that
checks both the top-level scheduler and `scheduleParameters` would have caught
all eight Grok near misses.

#### Top-up: connected the wallet through the wrong service

[Grok attempt 1](enterprise-long-horizon-trials/grok45/enterprise-top-up-billing-lifecycle/attempt-01/trajectory.json)
passes 3/11, while [Opus attempt 1](enterprise-long-horizon-trials/opus5/enterprise-top-up-billing-lifecycle/attempt-01/trajectory.json)
passes 11/11. The largest failure starts with one shortcut:

```ts
// Grok
const creditService = this.invoicesService.creditService;
const { balance } = await creditService.findCreditBalance({
    businessID: this.businessID,
    customerId: this.customerId,
});

// Opus
const { balance } = await this.creditService.findCreditBalance({
    businessID: this.businessID,
    customerId: customer?.customerId ?? this.customerId,
});
```

Grok had already found that `InvoicesService` contains a `CreditService`, so it
used that convenient route. But an offering is also built in places where the
invoice-service test double does not contain that hidden nested property. The
[verifier output](enterprise-long-horizon-trials/grok45/enterprise-top-up-billing-lifecycle/attempt-01/verifier-test-stdout.txt)
shows five wallet checks crashing on `findCreditBalance`. One bad connection
disabled balance checks, charging, hourly deduction, overdraft handling, and
the zero-usage path.

The same run also used a customer-specific scheduler ID and duplicated
create/update validation instead of exposing one shared validator. That caused
three more failures. Opus traced who owns each dependency: the offering gets
direct access to the wallet service, the offering ID owns the hourly schedule,
and one validator is called by both create and update. It then added tests for
the wallet, scheduler, and payment paths. This is why the comparison is 3/11
versus 11/11, not a small edge-case difference.

**Where to improve:** before reusing a nearby service, trace every constructor,
factory, and test double that builds the object. Give a dependency directly to
the object that owns the behavior. Then run one full workflow test that starts
at enrollment, deducts usage, reads the wallet, and tops it up.

#### S3: built the pieces but did not verify the full data path

[Grok attempt 5](enterprise-long-horizon-trials/grok45/enterprise-s3-datastore-measurement/attempt-05/trajectory.json?raw=1)
passes 5/10, while [Opus attempt 1](enterprise-long-horizon-trials/opus5/enterprise-s3-datastore-measurement/attempt-01/trajectory.json?raw=1)
passes 10/10. Grok added the IAM setup, persistence fields, connector endpoint,
and dead-letter path, but two public methods only changed their input object and
silently returned `undefined`:

```ts
// Grok
dbAccessInformation.iamRoleArn = createRoleResponse.Role?.Arn;
dbAccessInformation.externalId = externalId;
dbAccessInformation.ingestion = ingestion;
dbAccessInformation.dlq = dlq;
// method ends without returning dbAccessInformation

// Opus
dbAccessInformation.dlq = dlq;
return dbAccessInformation;
```

The [verifier output for attempt 5](enterprise-long-horizon-trials/grok45/enterprise-s3-datastore-measurement/attempt-05/verifier-test-stdout.txt)
shows `Received: undefined` for setup and trust update. The create path also
returned non-canonical ingestion and dead-letter locations. In the failed-record
path, Grok reused a storage helper without testing it through the connector
boundary; the hidden test then reached an unconfigured AWS client and crashed
before the dead-letter record was written. Together, these mistakes broke
provisioning, update, persistence, and both malformed-record checks.

Opus followed each generated value through four stages: create it, return it,
persist it, and return it again from the service. It also tested the malformed
record path through a controllable S3 boundary and returned a clear dead-letter
result. Grok's existing tests all passed, but they did not cover those end-to-end
contracts, and the run ended without reviewing the final diff.

**Where to improve:** for every public method, test both its side effects and
its return value. For external integrations, run one success path and one
failure path with the client mocked at the same boundary the production code
uses. Do not stop after the build passes when the task spans setup, storage,
API return, and error handling.

Across the top-up and S3 pairs, the clearest difference is final contract
closure. Grok can find the right files and write substantial local code, but it
often accepts the first plausible connection and stops when the pieces exist.
Opus more reliably traces ownership, checks every construction path, tests the
boundaries between services, and compares the final repository with the
original request. In simple terms: Grok builds the parts; Opus more reliably
makes the whole system work.

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
[`long-horizon-enterprise-results.json`](indexes/long-horizon-enterprise-results.json),
[`enterprise-long-horizon-trials/`](enterprise-long-horizon-trials/), and
[`long-horizon-enterprise-artifacts-manifest.json`](manifests/long-horizon-enterprise-artifacts-manifest.json).

## Bug-injection debugging analysis

### Bug-task pass@k results

Each model/task cell has ten verifier-valid attempts. Using the unbiased
estimator `1 − C(n−c, k) / C(n, k)`, the task-level comparison is:

| Task | Required checks | Model | Solves (c/n) | pass@1 | pass@3 | pass@10 |
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
| **Macro mean** | **152 total** | **Grok 4.5** | **21/80** | **0.2625** | **0.3833** | **0.5000** |
| **Macro mean** | **152 total** | **Claude Opus 5** | **55/80** | **0.6875** | **0.8344** | **0.8750** |

The summary solve values are sums across task cells; pass@k is the unweighted
macro mean of the eight task-level estimators. pass@10 is the task-coverage
measure because each cell has ten attempts. The comparison therefore shows both a repeatability gap,
21/80 versus 55/80, and a breadth gap, four of eight tasks with a Grok solve
versus seven of eight with an Opus solve.

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
operation. For example, [Grok phone attempt 1](bug-injection-trials/grok45/latent-phone-invites/attempt-01/trajectory.json)
and [Opus phone attempt 1](frontier-trials/opus5/latent-phone-invites/attempt-01/trajectory.json)
both solve the task. The Grok trace fixes the international prefix by consuming
both zeroes, then preserves the configured region by taking the first plausible
fallback:

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

[Grok attempt 5](bug-injection-trials/grok45/latent-doc-extractors/attempt-05/trajectory.json)
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

The [Grok verifier output](bug-injection-trials/grok45/latent-doc-extractors/attempt-05/verifier-output.json)
shows the consequence: the two-line rent roll now works, but a single stray
rent line is incorrectly accepted. All ten Grok attempts fail that negative
pin. Six Opus attempts solve the task; the other four make the same one-line
over-generalization, so the separation is repeatability at preserving both
sides of a semantic boundary rather than exclusive access to the solution.

**Where to improve:** for every relaxed threshold, generate and replay the
below-boundary, exact-boundary, and above-boundary cases before stopping. A
three-row local table for counts 1, 2, and 3 would have exposed the regression.

#### Financial tools: one ticket condition never reaches the diff

[Grok attempt 1](bug-injection-trials/grok45/latent-financial-tools/attempt-01/trajectory.json)
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

The [Grok verifier output](bug-injection-trials/grok45/latent-financial-tools/attempt-01/verifier-output.json)
shows that zero and two severe lates behave correctly but exactly one does not.
Every Grok attempt leaves this same check failing. Opus solves three of ten;
the remaining seven also miss it, so this is another repeatability gap around
complete ticket-to-diff reconciliation.

**Where to improve:** maintain a case-level checklist whose entries close only
when the corresponding symbol appears in the final diff or a test proves that
no edit is needed. For this case, searching each ticket noun and replaying
`late_90` values 0, 1, and 2 would prevent the silent omission.

#### Txenrich: broad regex expansion instead of one exact width

[Grok attempt 2](bug-injection-trials/grok45/xrepo-txenrich-latent/attempt-02/trajectory.json)
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

The [Grok verifier output](bug-injection-trials/grok45/xrepo-txenrich-latent/attempt-02/verifier-output.json)
shows both regressions: a 15-character remark becomes a cheque deposit and a
non-zero-prefixed 16-character remark is also accepted. Eight of ten Grok
attempts break the 15-character pin, while Opus solves nine of ten by changing
the one exact width rather than generalizing the parser family.

**Where to improve:** prefer the smallest predicate change consistent with the
symptom, then diff outputs on the target row and its nearest negative siblings.
Do not propagate a regex widening across bank modules without evidence that
each module shares the same contract.

#### Txenrich3: correct symptom family, wrong bank implementation

[Grok attempt 5](bug-injection-trials/grok45/xrepo-txenrich3-latent/attempt-05/trajectory.json)
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

The [Grok verifier output](bug-injection-trials/grok45/xrepo-txenrich3-latent/attempt-05/verifier-output.json)
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
capability gap. [Grok attempt 1](bug-injection-trials/grok45/xrepo-txenrich4-latent/attempt-01/trajectory.json)
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

The [Grok verifier output](bug-injection-trials/grok45/xrepo-txenrich4-latent/attempt-01/verifier-output.json)
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
[`grok_trials.json`](indexes/grok_trials.json), [`opus5_trials.json`](indexes/opus5_trials.json),
[`bug-injection-trials/grok45/`](bug-injection-trials/grok45/), and [`frontier-trials/opus5/`](frontier-trials/opus5/).

## Native-table migration difficulty control

The earlier `long-native-table-migration` study is retained as a shared
difficulty control rather than a Grok-specific capability gap. Its final
comparison contains nine valid attempts, three each for Opus 5, Grok 4.5, and
GPT-5.6 Sol. All three models solved **0/3**, so Opus independently exceeds the
50% difficulty threshold. Tool calls ranged from **80 to 169**, with a
conventional nine-trial median of **116**. Six traces
exceeded the original 70–100 reference band; the checked-in
`indexes/long_horizon_results.json` correctly treats that band as descriptive, reports
the difficulty gate as true, and sets overall `qualifies: true`.

The control keeps OpenCode 1.18.13 and the Daytona snapshot fixed. Valid scored
trials use the exact OpenRouter routes for all three models. Zero-turn transport
attempts are excluded as infrastructure failures rather than counted as model
failures.

pass@k uses `1 − C(n−c, k) / C(n, k)`. Every model has three valid attempts on
the six-check task:

| Task | Required checks | Model | Solves (c/n) | pass@1 | pass@3 | Task coverage (pass@3) |
|---|---:|---|---:|---:|---:|---:|
| Native-table migration | 6 | Grok 4.5 | 0/3 | 0.0000 | 0.0000 | 0.0000 |
| Native-table migration | 6 | Claude Opus 5 | 0/3 | 0.0000 | 0.0000 | 0.0000 |
| Native-table migration | 6 | GPT-5.6 Sol | 0/3 | 0.0000 | 0.0000 | 0.0000 |

Here pass@3 is also task coverage because `n=3`.

### Native-table measured effort

| Model | Valid trials | Model turns | Tool calls, median (range) | Trial wall time, mean / median (range) |
|---|---:|---:|---:|---:|
| Grok 4.5 | 3 | 110 | 116 (108–134) | 11m 41.9s / 11m 09.2s (10m 11.9s–13m 44.7s) |
| Claude Opus 5 | 3 | 437 | 168 (148–169) | 56m 52.7s / 50m 07.4s (41m 46.6s–78m 44.2s) |
| GPT-5.6 Sol | 3 | 113 | 90 (80–90) | 8m 24.9s / 8m 41.1s (7m 35.9s–8m 57.8s) |

| Model | Attempt | Reward | f2p | p2p | Model turns | Tool calls | Full trial wall time | Input tokens (cached) | Output tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Opus 5 | 1 | 0 | 0/4 | 1/2 | 150 | 169 | 50m 07.4s | 34.89M (34.89M) | 143.9k |
| Opus 5 | 2 | 0 | 1/4 | 1/2 | 154 | 168 | 78m 44.2s | 38.24M (38.24M) | 150.7k |
| Opus 5 | 3 | 0 | 0/4 | 1/2 | 133 | 148 | 41m 46.6s | 26.20M (26.20M) | 125.0k |
| Grok 4.5 | 1 | 0 | 1/4 | 2/2 | 39 | 134 | 11m 09.2s | 2.80M (2.67M) | 32.7k |
| Grok 4.5 | 2 | 0 | 1/4 | 1/2 | 36 | 116 | 13m 44.7s† | 2.72M (2.52M) | 31.4k |
| Grok 4.5 | 3 | 0 | 1/4 | 2/2 | 35 | 108 | 10m 11.9s | 2.71M (2.50M) | 28.2k |
| GPT-5.6 Sol | 1 | 0 | 1/4 | 1/2 | 37 | 80 | 7m 35.9s | 2.24M (2.24M) | 13.4k |
| GPT-5.6 Sol | 2 | 0 | 1/4 | 1/2 | 40 | 90 | 8m 41.1s | 2.73M (2.73M) | 14.1k |
| GPT-5.6 Sol | 3 | 0 | 1/4 | 1/2 | 36 | 90 | 8m 57.8s | 2.73M (2.73M) | 15.1k |

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
trial index.

### Native-table verifier contract

The hidden suite checks behavior rather than candidate file names, class names,
commit hashes, or similarity to the historical patch. Its six tests map
directly to the six numbered prompt requirements:

| Prompt requirement | Hidden verifier method | Observable contract |
|---|---|---|
| Native grid, box, and text-aligned extraction | `nativeStrategiesProduceStructuredRows` | Three repository PDFs produce the expected structured cells |
| Bank-family policy selection | `supportedBankFormatsUseCorrectPolicy` | Seven bank and format fixtures select working native policies |
| Native success bypasses remote extraction | `nativeSuccessSkipsRemoteExtractor` | Native output is nonempty and neither the remote processor nor mapper is called |
| Unknown input retains remote fallback | `unsupportedFormatsRetainRemoteFallback` | An unknown bank identifier reaches the existing remote processor and mapper |
| Native, ML, and fallback status is observable | `usageStatusPropagatesToApiAndLogs` | Three semantic states round-trip through API and log objects |
| Existing date behavior is unchanged | `legacyDateParsingRemainsStable` | Historical date parsing and blank-input behavior stay green |

Three mechanical controls ran in the same Linux/AMD64 image. The untouched base
scored 0, with all four fail-to-pass checks failing and both preservation checks
passing. The historical oracle scored 1. An alternate oracle also scored 1 after
all seven concrete dependency setters were removed; the verifier found compatible
dependencies by type and injected fields, so it did not require the historical
wiring shape. Raw control outputs remain under `long-horizon-controls/`.

### Native-table trace analysis

The nine traces reach the same zero score through different implementation
paths. This is evidence of a shared end-to-end difficulty, not a Grok-specific
capability gap. Every model produced code that compiled and looked plausible,
but none completed the full contract across native extraction, policy choice,
remote fallback, downstream acceptance, and diagnostics.

| Model | Trace pattern | Best f2p | Best p2p | Main missing behavior |
|---|---|---:|---:|---|
| Claude Opus 5 | Large refactor with separate readers, geometry helpers, extractors, policies, and validation | 1/4 | 1/2 | The final service could not be exercised through the established dependency boundary, and native fixture outputs remained empty |
| Grok 4.5 | Broad heuristic implementation followed mainly by package-build checks | 1/4 | 2/2 | Native tables were never accepted as structured output, even when nearby fallback behavior stayed intact |
| GPT-5.6 Sol | Compact generic extractor exposed through three policy names | 1/4 | 1/2 | Policy selection did not become three meaningfully different extraction behaviors, and unsupported fallback regressed |

Across all nine attempts, the hidden verifier accepted no native structured
result. Where extraction reached the core fixtures, the verifier observed
empty structured cells. The best regression preservation came from Grok
attempts 1 and 3, which passed both preservation checks, but they still failed
all three native extraction, policy, and remote-skip checks. The linked traces
below show why compilation was not enough.

#### Grok: compile success masked an unusable native result

[Grok attempt 1](long-horizon-trials/grok45/attempt-01/trajectory.json) is paired
with [Opus attempt 2](long-horizon-trials/opus5/attempt-02/trajectory.json), the
closest Opus run by required checks. The Grok run added separate geometry-based
builders and hybrid routing. It ended by reporting a successful offline package
build. The builder, however, initialized every new table as non-transactional
and depended on later analysis to change that state:

```java
table.setBankTransactions(false);
```

That is not proof of the failure by itself, but it is consistent with the
integration result: the verifier never received an accepted native table and
reported empty structured cells for every required fixture. Late in the trace,
the model also narrowed one helper flow to a single hard-coded format family:

```java
bankStatementVO.setBank("HDFC");
documentExtractionRequest.setBankName("HDFC");
```

It then reran the package build rather than replaying the supported-format
matrix. This explains the gap between the final report and the measured
behavior. The implementation had many of the right pieces, but it did not
prove that one real fixture became a non-empty transaction table, flowed
through the existing consumer, and skipped the remote extractor. A better
completion loop would verify that vertical slice first, then repeat it across
every policy family and the unsupported fallback case.

#### GPT-5.6 Sol: policy labels without policy-specific behavior

[GPT-5.6 Sol attempt 1](long-horizon-trials/gpt56sol/attempt-01/trajectory.json)
introduced three policy names, but routed them through one main table-building
algorithm. The clearest policy-specific branch only filtered rows for the
text-aligned case:

```java
if (policy == NativeTablePolicy.TEXT_ALIGNED_ROW_SELECTED
        && !foundTransaction && !dateRow) {
    continue;
}
```

The bordered-grid and box-guided policies did not receive equivalent,
layout-specific extraction logic in that path. The model's own tests checked
policy selection and broad table shape, while the hidden verifier checked
exact structured results on the real fixture families. All three Sol attempts
therefore passed the diagnostics check but produced empty native results and
failed the unsupported-format fallback check. The improvement target is to
test a different observable behavior for each policy, using one exact fixture
per family before expanding the mapping table.

#### Opus 5: broad implementation, broken integration seam

[Opus attempt 2](long-horizon-trials/opus5/attempt-02/trajectory.json) was the
closest Opus run by required checks. The Opus traces spent far more turns on a
large architecture with page readers, word extraction, vector geometry,
multiple native extractors, a policy registry, validation, and a shared
analysis pipeline. That breadth still did not close the application boundary.
The final behavioral harness could not configure the refactored service:

```text
AzureDocumentExtractionServiceImpl has no dependency slot for AnalyzeDocuments
```

The verifier had already been repaired to find compatible dependencies by type
through fields or setters, so this was not the old setter-name assumption. The
refactor no longer exposed a compatible service path that the application-level
test could instantiate. Opus attempt 3 reached the fixtures but still returned
empty structured cells. Together, these traces show that more code and more
turns did not replace an end-to-end check through the original service
boundary. The improvement target is to preserve that boundary during the
refactor and run one fixture through the same construction and injection path
used by production before adding more components.

### General takeaway from the control

The shared weakness is executable contract closure. All three models could
explore the repository, propose a reasonable design, compile a large patch,
and describe the intended behavior. None verified the complete chain on the
real fixture corpus:

1. A supported PDF produces the exact non-empty structured rows.
2. The selected policy changes how extraction works, not only its label.
3. A successful native result is accepted downstream and skips the remote call.
4. An unsupported format still calls the remote extractor.
5. The chosen path appears in the API response and persisted diagnostics.
6. Legacy date parsing remains unchanged.

The most useful improvement target is a fixture-first vertical slice. Complete
and verify one policy through all six boundaries, then add the other policy
families without changing the shared routing contract. This same environment
can provide stepwise feedback at each boundary without adding a new task.

## Nature of the source codebases

The evaluation covers five authorized private production systems. After
excluding dependencies, generated and build output, and Git metadata, the
agent-visible snapshots contain **1,789 code files** and **269,074 code LOC**
across Python, TypeScript, JavaScript, and Java. They also expose **149 test
files** and **135 PDF fixtures**. Across the two evaluation tracks and the
separate difficulty control, these systems support **12 task instances** and
**187 required checks**.

| Source system | Language mix by code LOC | Agent-visible snapshot | Evaluation scope | Tasks represented |
|---|---|---|---|---|
| Financial workflow backend | 54.0% Python<br>46.0% TypeScript | 521 code files / 133,848 LOC<br>33 test files / 3,686 test LOC | 4 bug tasks<br>20 planted defects, 19 reward-gated<br>78 required checks | credit-normalize<br>doc-extractors<br>financial-tools<br>phone-invites |
| Financial integration service | 100% Java | 264 code files / 16,375 LOC<br>17 test files / 2,823 test LOC | 1 bug task<br>5 planted defects<br>19 required checks | FIU |
| Transaction-enrichment service | 100% Python | 52 code files / 11,179 LOC<br>no candidate-visible test files | 3 bug tasks<br>15 planted defects<br>55 required checks | txenrich<br>txenrich3<br>txenrich4 |
| Billing and measurement platform | 99.5% TypeScript<br>0.5% JavaScript | 539 code files / 66,319 LOC<br>99 test files / 20,475 test LOC | 3 long-horizon tasks<br>68 oracle files / 3,602 changed LOC<br>29 required checks | Customer billing-schedule migration<br>Top-up billing lifecycle<br>S3 datastore measurement |
| Document-processing platform | 100% Java | 413 code files / 41,353 LOC<br>135 PDF fixtures | 1 difficulty control<br>62 commits / 70 files / approximately 13,000 added LOC<br>6 required checks | Native-table migration difficulty control |

Code-file and LOC counts include candidate-visible tests; the test counts are
subsets shown separately. Dependency trees, compiled output, generated output,
and Git metadata are excluded. The transaction-enrichment snapshot intentionally
has no candidate-visible tests, but its three tasks are independently graded by
55 hidden checks.

The eight bug-injection tasks alter **40 narrow boundaries**, of which **39 are
reward-gated**, while preserving the surrounding systems. The three enterprise
long-horizon tasks start from pre-feature production revisions and use
historical changes spanning **68 oracle files** and **3,602 changed LOC** only
as solvability references. The separate native-table control condenses **62
production commits**, **70 files**, and approximately **13,000 added LOC** into
one six-check task. Independently written hidden tests grade observable behavior
rather than source similarity.

Company names, ticket identifiers, commit messages, credentials, customer
records, and unrelated configuration are removed, while the architecture and
task-relevant dependencies remain intact. The evaluation therefore rests on
measured code volume, verifier scope, behavior, controls, and traces rather than
the reputation of any source company.

## Conclusion

On the two enterprise tasks with clear end-to-end requirements, Grok usually
found the right part of the codebase and wrote much of the requested feature.
Its remaining failures came from rules applied in one path but not another,
values created but not returned or saved, and tests that checked individual
pieces rather than the full workflow.

| What Grok can improve | Evidence | What to train |
|---|---|---|
| Apply each rule everywhere it matters | Top-up billing lifecycle | List each allowed and rejected case, then test it during create, update, and scheduled execution. |
| Carry generated values through the full workflow | S3 datastore measurement | Check that each value is created, returned, saved, and returned again by the service, including the bad-record path. |
| Prove the complete behavior before stopping | Top-up billing lifecycle<br>S3 datastore measurement | Run one test through the real entry point and tie every completion claim to a passing check or inspected final object. |

The practical target is straightforward: keep every requirement active until
the final code and an end-to-end test show that it works across the complete
workflow.

## Appendix

### Long-horizon definition and evaluation bar

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
