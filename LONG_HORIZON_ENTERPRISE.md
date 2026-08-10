# Long-horizon enterprise capability-gap study

## Executive result

This study freezes three enterprise-derived production tasks at eight
independent Grok 4.5 attempts and eight independent Claude Opus 5 attempts per
task. Every accepted attempt used the exact model route, OpenCode 1.18.13, one
isolated Daytona sandbox, the frozen task checksum, a denied subagent/task
tool, and a complete hidden-verifier result.

| Task | Grok 4.5 | Claude Opus 5 | Opus minus Grok | XAI gate |
|---|---:|---:|---:|---|
| Customer billing-schedule migration | 0/8 (0%) | 7/8 (87.5%) | +87.5 pp | qualifies |
| Top-up billing lifecycle | 0/8 (0%) | 7/8 (87.5%) | +87.5 pp | qualifies |
| S3 datastore measurement | 0/8 (0%) | 5/8 (62.5%) | +62.5 pp | qualifies |
| **Total** | **0/24 (0%)** | **19/24 (79.2%)** | **+79.2 pp** | **3/3 qualify** |

The meeting's explicit learnability filter was: run eight rollouts and accept
Grok solving one to six, or accept zero when a comparable model such as Opus 5
can complete the task (transcript line 20). All three tasks qualify through
that second branch. A 0/8 estimate is still statistically uncertain: its 95%
Wilson interval is 0–32.4%. The raw eight-attempt evidence, rather than the
point estimate alone, is therefore the procurement claim.

The selected 48-attempt cohort cost **$270.47**. The 32 accepted attempts used
to finish the matrix cost **$148.24** and completed in **59m 44s** of overlapping
wall clock. Conservative project spend, including exploratory, invalid, and
superseded-checksum work, is **$1,940.18**, below the $2,500 target and $3,000
hard cap.

## Why these are long-horizon tasks

Long horizon here is both structural and measured. These are not large library
imports or single-file patches: each task crosses persistence, service,
validation, scheduler, queue, billing, AWS, or failure-recovery boundaries.
Their source evidence spans multiple engineering days, and the evaluated agents
used up to 168 model turns and 40 minutes of agent execution on one attempt.

| Task | Packaged oracle | Historical evidence | Human estimate | Coupled surface |
|---|---:|---|---:|---|
| Billing schedule | 23 files / 343 LOC | 56 files, +1,447/-855 over 4 days | 3 days | customer enrollment, invoice periods, ledger, queues, empty usage |
| Top-up lifecycle | 28 files / 1,450 LOC | 35 files, +1,569/-325; 21 commits over 6 days; 18.5 ticket days | 3 days | DTO/entity/persistence, hourly scheduling, wallet credit, invoice and overdraft ordering |
| S3 measurement | 17 files / 1,809 LOC | four PRs over 3 days; 17.8 ticket days | 5 days | nested configuration, IAM trust/policy, persistence, connector routing, mirrored DLQ writes |

The S3 changed-LOC figure includes a dependency lockfile, which is why file
count, behavioral boundaries, engineering history, agent turns, and wall time
are reported alongside LOC. The task's difficulty claim does not rest on that
lockfile.

Prompts are not verbatim ticket copies. They consolidate observable behavior
from the actual tickets, PRs, and code history while removing ticket IDs,
commit messages, file lists, and implementation hints. The historical change
is retained as the solvability oracle; independently written hidden assertions
grade the visible contract.

## Binary win conditions

A reward of 1 requires every configured fail-to-pass and pass-to-pass assertion
to pass. Partial implementations receive reward 0.

### Customer billing-schedule migration — 8 required checks

- Construct the migrated billing service without binding the grader to Nest
  constructor order.
- Create a monthly billing schedule only for a customer with an offering.
- Replace an enrolled customer's schedule on an offering change and tolerate an
  already-missing old schedule.
- Resolve the customer billing cycle, call the usage-total invoice path with the
  exact range, and persist the invoice identity in the billing ledger.
- Route billing emissions only to the billing queue and retain non-billing
  emissions on the data queue.
- Return empty usage for a customer with no offering.

### Top-up billing lifecycle — 11 required checks

- Validate cycle/type compatibility, required top-up fields, and the default
  threshold; persist and read the new fields.
- Create one hourly offering-level scheduler with a stable ID.
- Refill only below the threshold, charge the exact wallet gap, and store the
  payment as credit.
- Deduct full hourly usage, including overdraft usage, before evaluating refill;
  issue no usage invoice and create no credit mutation for zero usage.
- Preserve existing non-top-up billing behavior.

### S3 datastore measurement — 10 required checks

- Apply default platform/region values and persist/read every generated access
  and endpoint field.
- Provision a uniquely named, prefix-scoped IAM role/policy with customer trust
  and a fresh external ID; preserve role/external ID while updating trust.
- Return the complete provisioned measurement configuration from create.
- Route valid connector records through usage creation using the business ID in
  the S3 key.
- Mirror malformed records to the DLQ with the required suffix and metadata,
  including already-relative source keys.
- Preserve existing measurement modes.

## Measured agent horizon

Agent wall time excludes sandbox setup and grading. Trial wall time includes
those phases and remote scheduling/provider latency.

| Model / task | Turns, mean | Tool calls, mean | Agent time, median (range) | Longest trial | Cost |
|---|---:|---:|---:|---:|---:|
| Grok / billing | 17.3 | 64.4 | 2.9m (2.8–3.7m) | 25.3m | $3.45 |
| Opus / billing | 62.3 | 67.1 | 10.5m (7.9–12.2m) | 22.8m | $30.59 |
| Grok / top-up | 54.6 | 161.4 | 13.6m (10.6–19.2m) | 58.6m | $18.75 |
| Opus / top-up | 149.9 | 149.6 | 27.5m (21.6–40.2m) | 59.7m | $138.44 |
| Grok / S3 | 22.1 | 74.0 | 5.7m (5.2–18.4m) | 18.9m | $5.12 |
| Opus / S3 | 109.0 | 111.5 | 25.1m (19.7–36.3m) | 37.6m | $74.13 |

Across the full cohort the agents produced 3,321 model turns and 5,024 tool
calls. Top-up is the clearest measured long-context environment. Billing is
structurally long-horizon but Grok converges quickly to the same nearly complete
mistake; that repeatability is useful capability-gap evidence rather than a
claim that every individual billing rollout consumes an hour.

## Trace-backed failure modes

### Billing: requirement retention across a migration

All eight Grok attempts passed 7/8 checks and failed only schedule replacement.
In the representative trace, Grok restates that subject and business identity
must be preserved and its final summary claims they are preserved, yet both the
create and replacement code write only `customerId` into
`scheduleParameters`. The implementation is coherent, builds, and passes the
candidate-visible suite; it drops one explicit cross-module field invariant
while editing the larger migration. This is an execution/requirement-retention
gap, not repository localization or a no-op.

Opus passed seven attempts. Its one failure passed 7/8 but never called the
usage-total invoice boundary. The fair verifier passes both valid dependency
orders, so this remaining miss is behavioral rather than constructor coupling.

### Top-up: state-machine and exact-boundary composition

Grok's scores were 3/11, 3/11, 8/11, 3/11, 3/11, 5/11, 5/11, and 9/11. Every
attempt missed the stable hourly scheduler ID; seven missed the non-top-up field
rejection. Six attempts each missed exact gap-to-target charging, full usage
deduction without a usage invoice, and overdraft-before-refill ordering. The
best trace reached 9/11 and failed only one validation boundary plus stable
scheduler identity. Grok can assemble most components, but it does not reliably
hold the complete wallet/scheduler state machine across a long edit sequence.

Opus passed 7/8. Its lone 10/11 miss was also the stable scheduler ID, showing
that this assertion is difficult but learnable rather than Grok-specific or
unsatisfiable.

### S3: cross-boundary API-contract precision

Every Grok attempt failed both the scoped IAM provisioning/returned-location
check and the create-persist-return configuration check. Six also missed the
mirrored malformed-record DLQ contract. Best attempts reached 8/10, so the
model localized the feature and implemented most of it, but repeatedly lost
exact output shape, location, persistence, or asynchronous DLQ semantics across
AWS and application boundaries.

Opus passed 5/8. Its failed attempts range from a 9/10 relative-key edge case to
broader IAM/trust/configuration/DLQ misses. That spread demonstrates real task
variance and avoids a verifier whose difficulty depends on one universally
missed, oracle-specific assertion.

No selected zero was caused by a provider error, sandbox failure, missing
trajectory, or incomplete verifier output.

## Fairness and validity controls

- Untouched base reward is 0 and historical oracle reward is 1 for every task,
  with zero control exceptions.
- Accepted task checksums are
  `2f37f40152612b938e9fab30384ec2c17083d7efab6c8a56564634affbca4bdc`
  (billing),
  `6f4175275a7e2da3eb53dc4a610abed9ca009632493e29b1bdd6c6e8d441f4c0`
  (top-up), and
  `90c6f4ffe3a3635480af1332d23be5cf232345dcedb8bc362b6cd6b8b34dcd05`
  (S3).
- A billing audit found that one older test instantiated decorated Nest
  dependencies by positional order. The test was changed to grade invoice
  behavior with either valid order, fresh controls passed, and all 16 attempts
  on the old checksum were excluded. Those diagnostics cost $31.58 and do not
  affect any advertised rate.
- Hidden tests exercise observable boundary objects and calls with offline
  mocks; AWS and database operations never leave the verifier process.
- Each accepted result matches the exact route, OpenCode version, Daytona
  snapshot, single-agent policy, task checksum, and complete verifier output.
- Full trajectories are credential-redacted, and every published artifact is
  covered by a SHA-256 manifest.

The remaining limitations are explicit: eight attempts produce wide confidence
intervals; results are conditional on this agent scaffold and model route;
historical task construction requires authorization to use the source data; and
the final XAI gate compares Grok with Opus, not every frontier model. GPT-5.6 Sol
evidence remains in the broader historical matrix but was not rerun in this
specific finalization requested for Grok and Opus.

## Alignment to the XAI meeting

The package answers the four concrete requests in the transcript:

1. **Eight rollouts and learnability filter (line 20):** eight valid attempts
   per task/model; all three pass the stated 0/8-with-Opus-completion branch.
2. **Analysis surface (line 27):** binary win conditions, pass rates, cost,
   turns, agent/trial wall time, complete traces, and recurring failure modes.
3. **General long horizon and enterprise discovery (line 30):** multi-day,
   multi-boundary billing and cloud tasks that produce long model trajectories
   and expose missing evaluation coverage.
4. **More likely procurement path (line 34):** not merely "we have long tasks,"
   but an enterprise-derived, reproducible discrepancy: Grok 0/24 versus Opus
   19/24, with near-miss traces that identify trainable gaps.

This is therefore evidence for the meeting's second, more differentiated path:
specific enterprise capability gaps with demonstrated learnability.

## Published evidence

- Machine-readable results:
  [`sample-run/long-horizon-enterprise-results.json`](sample-run/long-horizon-enterprise-results.json)
- Redacted full trajectories, results, and verifier output:
  [`sample-run/long-horizon-enterprise-trials/`](sample-run/long-horizon-enterprise-trials/)
- Artifact sizes and SHA-256 hashes:
  [`sample-run/long-horizon-enterprise-artifacts-manifest.json`](sample-run/long-horizon-enterprise-artifacts-manifest.json)
- Anonymized task prompts and fairness notes: [`tasks/`](tasks/)

Rebuild the selected cohort summary and artifact package with:

```sh
python3 harness/build_long_horizon_enterprise.py
python3 harness/audit_enterprise_tasks.py
```
