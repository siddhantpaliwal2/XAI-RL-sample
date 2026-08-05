# Reference plan: native PDF transaction-table migration

## Production provenance

This task condenses the real 62-commit migration from
`a03ff50b9e6868565ba88be5f7438f4ac7583138` through
`ef9c61f5ae3e5259f8753d000a66a4e18962ffbe` in
`bank-statement-parser`. The original branch changed 70 production files
(about 13,000 inserted lines) to add native PDF geometry/text extraction,
bank-format policy handlers, pipeline routing, fallback, and usage diagnostics.
The gold patch omits the branch's unrelated development-endpoint change and
also routes its implemented row-selected strategy through the native path.

## Implementation outline

1. Introduce structured table/word/row models plus extraction primitives for
   graphics grids, box-guided geometry, and text-position row selection.
2. Add reusable strategy/configuration objects and bank-specific format
   handlers, with ML extraction remaining the default policy.
3. Route native strategies through document analysis without touching the
   Azure client; retain Azure for the default strategy.
4. Carry the extraction status from a statement into account responses and
   request-document/request-account log entities.
5. Keep the existing below-date transaction parser and date normalization
   semantics intact while adapting them to native table output.

## Prompt-to-verifier contract

| Prompt requirement | Hidden verifier method |
|---|---|
| Three offline native layout families produce structured rows | `nativeStrategiesProduceStructuredRows` |
| Supported bank fixtures choose their format policy | `supportedBankFormatsUseCorrectPolicy` |
| Successful native extraction skips the remote client | `nativeSuccessSkipsRemoteExtractor` |
| Unknown/unsupported layouts retain remote ML | `unsupportedFormatsRetainRemoteFallback` |
| Native/ML/fallback status reaches API and log records | `usageStatusPropagatesToApiAndLogs` |
| Existing parsing semantics remain stable | `legacyDateParsingRemainsStable` |

The new native extraction, policy, native-routing, and diagnostics behaviors
are fail-to-pass. Remote fallback and legacy parsing are pass-to-pass because
the migration must preserve both existing paths. Structural discovery in the
hidden suite lets the unmodified base compile, permits alternative class and
property names, and reports independent behavioral failures instead of
collapsing into one compiler error. The strategy tests execute representative
real PDFs already present in the base repository; the routing tests mock only
the remote boundary.

## Fairness and difficulty

Every expected behavior is observable from the prompt and the repository's
existing architecture and fixtures. The verifier does not require historical
class names, source-file counts, commit hashes, or byte-identical code. A
different implementation passes if it exposes compatible behavior at the
existing Java service boundaries. The work is long-horizon because a complete
solution spans PDF geometry, normalized table models, ten format-policy
families, service routing, fallback, and persistence/API propagation—not
because of a hidden one-line convention.
