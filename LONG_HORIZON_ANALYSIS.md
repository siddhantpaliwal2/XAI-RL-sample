# Long-Horizon Task Analysis

## Executive summary

`long-native-table-migration` is a repository-scale feature migration derived
from a real 62-commit production branch. The historical change touched 70
production files, added roughly 13,000 lines, and connected PDF geometry,
native table extraction, bank-specific policy, service routing, remote-ML
fallback, API state, persistence diagnostics, and legacy parsing behavior.

Four frontier models received three independent attempts each through the same
OpenCode 1.18.13 agent and frozen Daytona environment. All 12 attempts returned
complete verifier verdicts, and none solved the task:

| Model | Solves | pass@1 | pass@2 | pass@3 |
|---|---:|---:|---:|---:|
| Claude Opus 5 | 0/3 | 0.000 | 0.000 | 0.000 |
| Claude Fable 5 | 0/3 | 0.000 | 0.000 | 0.000 |
| Grok 4.5 | 0/3 | 0.000 | 0.000 | 0.000 |
| GPT-5.6 Sol | 0/3 | 0.000 | 0.000 | 0.000 |

The result clears the intended difficulty gate: Opus 5 and Fable 5 each failed
at least 50% of valid attempts; in practice, both failed 100%. The task's
`qualifies` result is `true`.

## What the task asks the agent to do

The prompt has six numbered requirements, each corresponding one-to-one with a
hidden verifier method:

| Requirement | Hidden test | Behavioral contract |
|---:|---|---|
| 1 | `nativeStrategiesProduceStructuredRows` | Grid, box-guided, and text-aligned PDFs produce correct structured cells |
| 2 | `supportedBankFormatsUseCorrectPolicy` | Seven real bank/format fixtures select a working native policy |
| 3 | `nativeSuccessSkipsRemoteExtractor` | Successful native extraction bypasses the remote processor and mapper |
| 4 | `unsupportedFormatsRetainRemoteFallback` | An unknown bank family still reaches the existing remote-ML boundary |
| 5 | `usageStatusPropagatesToApiAndLogs` | Native, ML, and native-to-ML fallback states survive through API and persisted log objects |
| 6 | `legacyDateParsingRemainsStable` | Existing date and blank-input behavior remains unchanged |

The agent sees the repository and the natural-language requirements. The gold
test is injected only at grade time. The verifier checks behavior rather than
class names, file names, commit identity, or similarity to the historical
patch.

## Experimental design

- Agent: OpenCode 1.18.13, with its subagent/task tool disabled.
- Environment: one isolated 2-CPU/4-GB Daytona sandbox per attempt, using the
  same frozen snapshot.
- Sampling: three independent valid attempts per model.
- Routes: exact OpenRouter routes for Opus 5, Fable 5, Grok 4.5, and GPT-5.6
  Sol.
- Timeout: 9,000 seconds, used as a safety bound rather than a target.
- Validity rule: an attempt enters the denominator only when the model runs and
  the hidden suite returns all six test verdicts.
- Scoring: reward 1 requires all fail-to-pass and pass-to-pass tests to pass;
  partial implementations receive reward 0.
- Frozen task checksum:
  `9f909fc28cd1d3c80d364b8086e66ac9c215e0d38ef2b812c6efd95be686d698`.

pass@k uses the unbiased estimator
`1 - C(n - c, k) / C(n, k)`. Because each model has `n=3` and `c=0`, its
measured pass@1, pass@2, and pass@3 are all zero.

## Result and effort profile

| Model | Model turns | Tool calls, median (range) | Trial wall time, mean / median (range) | Model cost |
|---|---:|---:|---:|---:|
| Claude Opus 5 | 437 | 168 (148-169) | 56m 52.7s / 50m 07.4s (41m 46.6s-78m 44.2s) | $68.42 |
| Claude Fable 5 | 367 | 148 (120-179) | 71m 22.0s / 75m 06.9s (61m 13.5s-77m 45.4s) | $126.01 |
| Grok 4.5 | 110 | 116 (108-134) | 11m 41.9s / 11m 09.2s (10m 11.9s-13m 44.7s) | $4.00 |
| GPT-5.6 Sol | 113 | 90 (80-90) | 8m 24.9s / 8m 41.1s (7m 35.9s-8m 57.8s) | $7.20 |

Across the 12 valid trials, the agents used 1,027 model turns and 1,550 tool
calls. They consumed 193.80M input tokens, including 193.26M cached tokens, and
923.8k output tokens. The valid long-horizon matrix cost $205.63 in model calls.

Eleven durations are full Harbor wall time from `started_at` to `finished_at`,
including environment setup, agent setup, agent execution, and verification.
One Grok agent command completed successfully, but Harbor stalled during
post-agent sandbox collection. Its conservative 13m 44.7s duration ends at the
recovered agent-completion timestamp; the corresponding trial records a
different `duration_basis`. Independently running trial durations are not
summed.

## What the failures reveal

### 1. The shared bottleneck was the core native path

None of the 12 attempts passed any of these three tests:

- `nativeStrategiesProduceStructuredRows`
- `supportedBankFormatsUseCorrectPolicy`
- `nativeSuccessSkipsRemoteExtractor`

The models could make progress around the feature, but no attempt connected
fixture-level geometry, policy selection, structured output, and downstream
service routing into one working native extraction path. This is the clearest
cross-model failure signal in the evaluation.

### 2. Peripheral integration was much easier than extraction semantics

Every attempt preserved legacy date parsing. Grok and Sol also passed status
propagation in all three attempts, while Opus passed it once and Fable never
did. Remote fallback passed in two Grok and two Fable attempts, but in no Opus
or Sol attempt.

| Hidden test | Opus 5 | Fable 5 | Grok 4.5 | GPT-5.6 Sol |
|---|---:|---:|---:|---:|
| Native strategies | 0/3 | 0/3 | 0/3 | 0/3 |
| Bank policy | 0/3 | 0/3 | 0/3 | 0/3 |
| Native bypass | 0/3 | 0/3 | 0/3 | 0/3 |
| Remote fallback | 0/3 | 2/3 | 2/3 | 0/3 |
| Status propagation | 1/3 | 0/3 | 3/3 | 3/3 |
| Legacy parsing | 3/3 | 3/3 | 3/3 | 3/3 |

This separation matters: the zero rewards are not simply compilation failures
or blanket inability to edit the repository. Agents preserved regressions and,
depending on the model, implemented diagnostics or fallback. They failed where
multiple subsystems had to agree on the same runtime behavior.

### 3. More agent effort did not produce more behavioral progress

Fable spent $126.01 and averaged more than 71 minutes per attempt. Sol spent
$7.20 and averaged about 8.4 minutes. Despite the roughly 17.5x cost difference,
both finished 0/3. Opus and Fable also produced substantially longer traces than
Grok and Sol without passing any of the three central native-path tests.

This result does not show that shorter traces are intrinsically better. It shows
that, on this task, continued exploration and implementation volume did not
overcome an architectural integration bottleneck. Tool-call count is therefore
useful evidence about trajectory shape, but it is not a success proxy.

### 4. The task is long-horizon because of dependency depth, not a stopwatch

Tool calls ranged from 80 to 179, with a median of 127; nine attempts exceeded
the original 70-100 reference band. The stronger reason to classify the task as
long-horizon is structural: one short prompt represents a 62-commit, 70-file
migration spanning extraction algorithms, fixture-specific policy, service
routing, fallback, diagnostics, persistence, and regression preservation.

A model can terminate in under ten minutes and still have confronted a
long-horizon task unsuccessfully. Agent elapsed time measures the agent's
behavior, not the amount of dependent implementation required for a correct
solution.

## Verifier fairness and controls

The final suite was tested against three mechanical controls:

| Control | Result |
|---|---:|
| Untouched base | reward 0; 0/4 fail-to-pass and 2/2 pass-to-pass |
| Historical 62-commit oracle | reward 1; all six tests pass |
| Alternate field-wired oracle | reward 1; all six tests pass |

The alternate oracle removes all seven concrete dependency setter methods from
the historical extraction service. It still passes because the verifier finds
compatible services and injects dependencies by type through either setters or
fields. This demonstrates that the suite does not require the historical Spring
wiring shape or a textual imitation of the oracle.

The Opus and Fable worktrees were regraded against this final verifier. Grok and
Sol were run only after the verifier was frozen. Every included attempt executed
all six tests, so the reported zeroes are behavioral failures rather than
hidden-suite compilation errors.

## Interpretation and limitations

- Three attempts are enough to establish the observed 0/3 outcome, but not a
  precise estimate of a very small nonzero success probability.
- All models used one agent scaffold. The result measures the model-agent pair,
  not an agent-independent property of the base models.
- The task has production provenance, but no controlled human completion-time
  study. It should not be assigned a human-hours horizon from commit count or
  agent wall time alone.
- One Grok duration uses recovered agent-completion time, explicitly labeled in
  its artifact, rather than Harbor `finished_at`.
- Direct GPT-5.6 Sol probes worked through AWS Bedrock Mantle, but OpenCode's
  Bedrock transport closed before the first model turn. Those zero-turn runs are
  infrastructure exclusions. The three valid scored Sol attempts used its exact
  OpenRouter route.

## Reproducibility artifacts

- [Task prompt](tasks/long-native-table-migration/instruction.md)
- [Gold test](gold-tests/long-native-table-migration.java)
- [Four-model result matrix](sample-run/long_horizon_results.json)
- [Opus 5 per-attempt index](sample-run/long_opus5_trials.json)
- [Fable 5 per-attempt index](sample-run/long_fable5_trials.json)
- [Grok 4.5 per-attempt index](sample-run/long_grok45_trials.json)
- [GPT-5.6 Sol per-attempt index](sample-run/long_gpt56sol_trials.json)
- [Verifier fairness audit](sample-run/long-horizon-controls/fairness-audit.md)
- [Packaged trials and trajectories](sample-run/long-horizon-trials)

