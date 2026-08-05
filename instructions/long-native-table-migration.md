<uploaded_files>/app</uploaded_files>

# Native bank-statement table extraction migration

1. Add an offline native transaction-table path that produces structured rows for bordered-grid, box-guided, and text-aligned row-selected PDFs.
2. Select the appropriate native policy for the supported bank-format families represented by the repository's statement fixture corpus.
3. When a supported native layout succeeds, carry its result through downstream document analysis without invoking remote ML extraction.
4. Keep the existing remote ML path as the default for unknown or unsupported layouts.
5. Expose whether each statement and account used native, ML, or native-to-ML fallback through API objects and persisted request diagnostics.
6. Preserve the existing transaction and date-parsing behavior outside the new native path.

Verify with:

    cd /app && mvn -o -q -DskipTests package
