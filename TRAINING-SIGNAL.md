# Training signal and training readiness for XAI-RL-sample

The XAI tasks currently expose one final signal. The verifier reads the
configured `fail_to_pass` and `pass_to_pass` assertion names, looks up those
exact names in the test report, and returns `reward = 1` only when every
configured assertion is reported as passing. Any missing or failed required name
gives `reward = 0`. The rule itself is deterministic. A representative
implementation is the [top-up
verifier](https://github.com/siddhantpaliwal2/XAI-RL-sample/blob/main/tasks/enterprise-top-up-billing-lifecycle/tests/test.sh#L40-L54),
with the required names stored in [its task
configuration](https://github.com/siddhantpaliwal2/XAI-RL-sample/blob/main/tasks/enterprise-top-up-billing-lifecycle/tests/config.json#L7-L25).

That is reasonable for reporting task resolution once the verifier covers the
full instruction. It is too coarse as the only training signal. An attempt that
misses one boundary receives the same zero as an attempt that never builds.
Behavior absent from the configured list also contributes nothing to the result.

We should keep strict binary completion and add a separate partial-progress
score:

- `reward` is the evaluation result. It stays binary and becomes `1` only when
  every required behavior, build check, regression check, and integrity check
  passes.
- `soft_score` is the training signal. It ranges from `0` to `1` and records
  verified partial progress. It must not be reported as task completion.

The checks feeding both values should remain deterministic and binary. A
requirement either passes or fails. If five tests support one requirement, the
requirement receives `1` only when all five pass.

```text
requirement_i = 0 or 1
soft_score = sum(requirement_i * weight_i)
reward = 1 only if every required requirement is 1
```

Weights belong to requirements, not raw assertion counts. Adding several small
assertions for one behavior should not make that behavior worth more than a
security invariant checked by one integration test. The weights for a task must
sum to `1.0`, be versioned with the verifier, and be frozen before the scored
training run.

## Worked example: prepaid-credit top-up billing

An initial requirement map for `enterprise-top-up-billing-lifecycle` could be:

| Requirement ID | Deterministic check | Weight |
| --- | --- | ---: |
| `TOPUP-BUILD` | The application build succeeds | 0.10 |
| `TOPUP-CONTRACT` | Amount and threshold persist through write and read paths, with the threshold defaulting to `0.2` | 0.15 |
| `TOPUP-VALIDATION` | A top-up cycle without `topUpAmount` is rejected, and top-up fields are rejected on other cycles | 0.10 |
| `TOPUP-SCHEDULE` | One stable hourly offering-level schedule is created | 0.10 |
| `TOPUP-ENROLLMENT` | Real enrollment evaluates the wallet and performs the required refill | 0.15 |
| `TOPUP-HOURLY` | Usage is deducted before refill, overdraft is recorded, and the exact refill gap is charged | 0.20 |
| `TOPUP-REGRESSION` | Existing monthly, annual, invoice, and credit behavior remains passing | 0.20 |

Every row returns only `0` or `1`. Suppose the build, contract, scheduler,
hourly path, and regressions pass, while required validation and enrollment
refill fail:

```text
soft_score =
    (1 * 0.10)
  + (1 * 0.15)
  + (0 * 0.10)
  + (1 * 0.10)
  + (0 * 0.15)
  + (1 * 0.20)
  + (1 * 0.20)
  = 0.75
```

The stored result would be:

```json
{
  "topup_build": 1,
  "topup_contract": 1,
  "topup_validation": 0,
  "topup_schedule": 1,
  "topup_enrollment": 0,
  "topup_hourly": 1,
  "topup_regression": 1,
  "soft_score": 0.75,
  "reward": 0
}
```

The `0.75` distinguishes real progress from a no-op. The attempt is still not a
solution.

The new map closes two current gaps. The
[instruction](https://github.com/siddhantpaliwal2/XAI-RL-sample/blob/main/tasks/enterprise-top-up-billing-lifecycle/instruction.md#L5-L9)
requires `topUpAmount` for the top-up cycle and an enrollment refill. The
gold-test helper always supplies `topUpAmount: "100"`. Its negative case checks
top-up fields on a non-top-up cycle, not a missing amount on a top-up cycle
([gold
test](https://github.com/siddhantpaliwal2/XAI-RL-sample/blob/main/gold-tests/enterprise-top-up-billing-lifecycle/enterprise-top-up-billing-lifecycle.gold-spec.ts#L113-L152)).
The hourly tests use a mocked enrollment but do not call the real enrollment
flow and assert its refill behavior ([gold
test](https://github.com/siddhantpaliwal2/XAI-RL-sample/blob/main/gold-tests/enterprise-top-up-billing-lifecycle/enterprise-top-up-billing-lifecycle.gold-spec.ts#L238-L330)).

The weights above are a starting proposal. Mutation tests and partial rollouts
should show that they rank implementations in the intended order before they are
frozen.

## Other XAI verifier gaps to close

Apply the same requirement mapping to every task before training.

**S3 datastore measurement.** The instruction requires a fresh external ID and
IAM access scoped to the business's ingestion and DLQ prefixes
([instruction](https://github.com/siddhantpaliwal2/XAI-RL-sample/blob/main/tasks/enterprise-s3-datastore-measurement/instruction.md#L5-L9)).
The current provisioning test calls the path once and checks that the external
ID is a non-empty string, so a fixed constant can pass. Its policy check looks
for the two expected path substrings, which does not reject a policy that
contains those strings alongside wildcard access ([gold
test](https://github.com/siddhantpaliwal2/XAI-RL-sample/blob/main/gold-tests/enterprise-s3-datastore-measurement/enterprise-s3-datastore-measurement.gold-spec.ts#L195-L229)).
Add separate binary requirements for external-ID uniqueness across repeated
calls, exact trust conditions, and least-privilege resources. A failed security
requirement must keep `reward` at `0` even when the weighted score is high.

**Latent document extractors.** Five defects are planted and reversed by the
oracle, but the task's own reference plan records that only four are
reward-gated. The `_scan_after_label` defect is not exercised by its intended
path ([reference
plan](https://github.com/siddhantpaliwal2/XAI-RL-sample/blob/main/tasks/latent-doc-extractors/reference_plan.md#L62-L78)).
Give each planted defect its own requirement ID. Full reward then means all five
repairs were demonstrated.

**Long native-table migration.** The verifier's core helper reduces an
extraction result to a count of nested cells ([cell-count
helper](https://github.com/siddhantpaliwal2/XAI-RL-sample/blob/main/gold-tests/long-native-table-migration/long-native-table-migration.java#L260-L270)).
The tests then pair fixed fixture paths with exact expected counts ([fixture
assertions](https://github.com/siddhantpaliwal2/XAI-RL-sample/blob/main/gold-tests/long-native-table-migration/long-native-table-migration.java#L713-L738)).
This does not establish that transaction dates, descriptions, debit and credit
direction, amounts, balances, or row order are correct. Replace the count gate
with requirement checks over structured rows, and add seeded, held-out document
variants whose filenames and layouts are unavailable to the agent.

## Verifier boundary and evidence

A denser signal creates more targets for an agent to optimize, so the grading
boundary has to be fixed first. The current local runner copies the hidden
verifier into the agent's container and runs it against candidate-controlled
state
([runner](https://github.com/siddhantpaliwal2/XAI-RL-sample/blob/main/harness/run_attempt.py#L14-L18),
[grading
path](https://github.com/siddhantpaliwal2/XAI-RL-sample/blob/main/harness/run_attempt.py#L58-L64)).
The final verifier should run in a separate image after the agent stops.

The trial should transfer only declared outputs needed for grading. For these
code tasks, use a fixed artifact such as `/logs/artifacts/agent.patch` and
declare that path in `task.toml`. Verifier tests, configuration, dependencies,
and result paths stay verifier-owned. Save the candidate artifact, task version,
verifier version, component results, logs, environment identity, and trajectory
for every trial.

Terminal-Bench 3 separates agent and verifier containers, collects artifacts
after a trial, and uploads them into the verifier environment. Retaining the
artifact makes regrading possible after a verifier correction. See the [3.0
announcement](https://www.frontierbench.ai/announcement) and Harbor's [separate
verifier
documentation](https://www.harborframework.com/docs/tasks#verifier-environment-shared-vs-separate).

An infrastructure failure should not be converted into an ordinary model
failure. Use a separate trial status such as `infra_error` when the sandbox or
verifier fails independently of the candidate. Candidate-caused build failures
and test crashes remain `reward = 0`.

## Reward output

Harbor supports numeric multi-metric `reward.json` files. Reward Kit can keep a
strict `all_pass` aggregate beside a weighted aggregate ([Reward Kit
aggregation](https://www.harborframework.com/docs/rewardkit#aggregating-dimensions)):

```toml
[[reward]]
name = "reward"
aggregation = "all_pass"

[[reward]]
name = "soft_score"
aggregation = "weighted_mean"
```

Expose each requirement as one binary dimension. When several low-level tests
support one requirement, collapse them through one criterion that returns
`all(subchecks)`. Reward Kit otherwise averages multiple criteria inside a
dimension by default, which would make the requirement fractional before task
weights are applied. Detailed failures belong in `reward-details.json` and
verifier logs. The training pipeline must explicitly read `soft_score`.
Terminal-Bench 3 reports task resolution, so this secondary metric is our
addition.

## Calibration and splits

Before admitting a task to training, run the following controls:

- The untouched repository gets the expected low score.
- The oracle gets `soft_score = 1` and `reward = 1`.
- Deliberately partial patches fail only the requirement groups they violate.
- Shortcut mutations fail, including a constant external ID, wildcard IAM
  access, a missing enrollment refill, and dummy native-table cells.
- Repeated runs of the same candidate produce the same requirement values.
- Frontier-agent rollouts produce a useful spread of partial scores instead of
  landing almost entirely at zero and one.

Split data by task family, not by individual attempts. Closely related tasks
from the same base repository, migration, or planted-defect family stay in one
split. For example, the `xrepo-txenrich` sibling tasks should not be divided
across training and evaluation simply because their task IDs differ. Keep a
training pool, a small calibration pool, and a sealed evaluation pool. Only the
training pool exposes requirement details to the trainer. The sealed pool is not
used to tune test coverage, weights, prompts, or generator seeds.

We should copy Terminal-Bench's task and verifier discipline, not use its
evaluation instances as training data. The Terminal-Bench 3 announcement
explicitly marks its benchmark data as material that should not appear in
training corpora.

## References

- [Terminal-Bench 3.0 announcement](https://www.frontierbench.ai/announcement)
- [Terminal-Bench contribution
  guide](https://github.com/harbor-framework/terminal-bench/blob/main/CONTRIBUTING.md)
- [Terminal-Bench task-review
  automation](https://github.com/harbor-framework/terminal-bench/blob/main/docs/TASK_REVIEW_AUTOMATION.md)
- [Harbor task structure and separate verifier
  environments](https://www.harborframework.com/docs/tasks)
- [Harbor Reward Kit](https://www.harborframework.com/docs/rewardkit)
- [Harbor RL
  workflow](https://www.harborframework.com/docs/training-workflows/rl)
