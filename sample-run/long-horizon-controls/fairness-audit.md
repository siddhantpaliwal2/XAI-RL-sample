# Long-horizon verifier fairness audit

The hidden suite is behavioral: it never compares a candidate patch, file list,
class name, or commit hash with the historical implementation. Its six tests
map one-to-one to the six numbered requirements in the task prompt.

| Prompt requirement | Hidden verifier method | Observable contract |
|---|---|---|
| Native grid, box, and text-aligned extraction | `nativeStrategiesProduceStructuredRows` | Expected structured cells from three repository PDFs |
| Bank-family policy selection | `supportedBankFormatsUseCorrectPolicy` | Expected structured cells from seven bank/format fixtures |
| Native success bypasses remote extraction | `nativeSuccessSkipsRemoteExtractor` | Nonempty native output and no remote/mock mapper invocation |
| Unknown input retains remote fallback | `unsupportedFormatsRetainRemoteFallback` | Deliberately unknown bank ID reaches both remote processor and mapper |
| Native, ML, and fallback status is observable | `usageStatusPropagatesToApiAndLogs` | Three distinct semantic states round-trip through API and log objects |
| Existing date behavior is unchanged | `legacyDateParsingRemainsStable` | Historical date parse and blank-input behavior remain green |

Three mechanical controls were executed in the same Linux/AMD64 task image:

- Untouched base: reward 0; all four fail-to-pass tests fail and both
  pass-to-pass tests pass.
- Historical 62-commit oracle: reward 1; all six tests pass.
- Alternate field wiring: reward 1 after removing all seven concrete dependency
  setter methods from the oracle's extraction service. The verifier discovers
  compatible dependencies by type and injects fields, so it does not require
  the historical setter names or exact Spring wiring shape.

All six independently authored Opus 5/Fable 5 candidates were regraded and
executed all six tests under the final verifier. The three Grok 4.5 and three
GPT-5.6 Sol candidates were run only after that verifier was frozen, and also
executed all six tests. Their reward-zero outcomes therefore come from failed
behavioral assertions, not hidden-suite compilation failures.
