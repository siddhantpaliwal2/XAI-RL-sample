# Substrate Repositories

The original task bank was built on four real, private production codebases
(two Python, two Java) from the fintech-lending domain. The historical
enterprise extension adds anonymized production substrates in TypeScript
and Groovy. Every environment is pinned to an immutable base commit and sealed
without usable Git history; hidden tests arrive only at grading time.

A lesson encoded in this selection: **substrate size is the difficulty
lever.** Candidate tasks built on small repos (200–900 LOC, one or two files)
were all rejected as too easy - the agent simply reads the whole codebase and
there is no localization challenge. Every surviving task sits on a repo large
enough that finding the defective boundaries is most of the work.

---

## loangenus - `loangenus-repo:v1`

- **Language / size:** Python - 338 files, ~72k LOC
- **Domain:** AI-assisted commercial-real-estate lending platform: document
  ingestion and field extraction, credit-report parsing, bank/bureau/accounting
  analytics, CRE deal qualification and lender matching, CRM integrations.
- **Structure:** `loangen-agent/` (the agent backend the tasks target -
  `agent/documents/`, `agent/analytics/services/`,
  `agent/services/cre_qualification/`, `agent/integrations/`) plus
  `loangen-app/` (product app, out of scope for all tasks).
- **Test stack:** pytest, unittest-style suites with AsyncMock/MagicMock;
  fully offline and deterministic (pydantic Settings satisfied by dummy env
  baked into the image).
- **Tasks built on it (4):** `latent-credit-normalize`,
  `latent-doc-extractors`, `latent-financial-tools`, `latent-phone-invites`.
- **Why it's good substrate:** the workhorse. Deep, layered business logic
  with many pure deterministic helpers (string normalization, thresholding,
  ratio math) whose edge behavior is pinned by neighboring code - ideal for
  latent boundary defects that existing tests never touch.

## transaction-enrichment-python - `txenrich-repo:v1`

- **Language / size:** Python - 52 files, ~11k LOC
- **Domain:** bank-statement enrichment engine (2022-era production code):
  per-bank categorization scripts that read raw description/remark/amount/type
  off each transaction and derive category, subcategory and payee.
- **Structure:** `categorizationapp/categorizationapp/BankScripts/` - ~35
  bank-specific scripts (HDFC, ICICI, Axis, …) built on pandas/numpy
  `np.select` condition tables.
- **Environment quirks:** pinned 2022-era numpy/pandas so the original logic
  runs unchanged; several files carry CRLF line endings, which the task image
  preserves byte-exactly (defects are planted by byte-level replacement).
- **Tasks built on it (3):** `xrepo-txenrich-latent` (HDFC/ICICI),
  `xrepo-txenrich3-latent` (IDBI/Indusind), `xrepo-txenrich4-latent`
  (PNB/Canara) - disjoint bank pairs, so no two tasks share a defect site.
- **Why it's good substrate:** the condition-table idiom repeats across 35
  scripts, so the intended behavior of any one line is pinned by dozens of
  sibling occurrences - perfect for single-token sentinel/offset defects.

## fiu_adapter - `fiu-repo:v1`

- **Language / size:** Java - 264 files, ~16k LOC (Maven, Java 8 /
  `maven:3.9-eclipse-temurin-8`)
- **Domain:** FIU (Financial Information User) adapter for the Indian Account
  Aggregator ecosystem: consent/data-flow webservice with parsing, validation,
  crypto (Diffie-Hellman services, JWS signatures) and timestamp handling.
- **Structure:** multi-module Maven build (`webservice`, `kms`,
  `jws-signature`, `diffie-hellman-services`, …); the graded suite is pure
  JUnit 5 over parsing/validation/timestamp helpers - no Spring context, no
  DB, no network.
- **Environment notes:** the base image pre-installs sibling modules, warms
  the Maven cache and the Surefire JUnit-platform provider at build time so
  agent-side and grading-side `mvn test` runs are fast and offline.
- **Task built on it (1):** `xrepo-fiu-latent` - the only Java task in the
  bank, and proof the task recipe transfers across languages and build
systems.

## bank-statement-parser - `bank-statement-parser-repo:v1`

- **Language / size:** Java 17 - 980 files at the pinned base; the migration
  changes 70 production files and adds about 13k lines.
- **Domain:** bank-statement ingestion and transaction normalization across a
  large corpus of Indian-bank PDF formats, with Azure Document Intelligence as
  the pre-existing remote extraction path.
- **Structure:** Spring Boot service code under `src/main/java/`; 135 real PDF
  fixtures plus cached extraction data under `src/test/resources/`.
- **Environment notes:** Maven dependencies, Surefire and JUnit are warmed at
  image-build time; the agent and verifier run offline. Git history is
  collapsed before the agent sees the repository.
- **Task built on it (1):** `long-native-table-migration`, a real 62-commit
  feature migration adding native grid, box-guided and text-position table
  extraction, bank-format routing, remote fallback and usage diagnostics.
- **Why it's good long-horizon substrate:** the feature crosses geometry,
  normalized document models, format-policy handlers, service orchestration,
  API representation and persistence. A complete implementation cannot be
  reduced to grepping for a handful of nearby boundary defects.

## Metering and billing service - five historical snapshots

- **Language / stack:** TypeScript, NestJS, TypeORM, Jest.
- **Domain:** usage metering and billing, offering/customer ownership,
  scheduled invoicing, wallets, and cloud usage ingestion.
- **Tasks built on it (5):** dimension pricing tiers, top-up billing,
  S3-backed measurements, customer identity migration, and customer billing
  schedules.
- **Environment notes:** each task uses its own exact pre-change commit. Node
  dependencies are preinstalled in the Daytona snapshot, Git history is
  collapsed, and only unit tests run during grading.

## Email-infrastructure state machine - one historical snapshot

- **Language / stack:** TypeScript, Jest, document-database repositories.
- **Domain:** managed email inboxes, campaign associations, deliverability,
  reputation, ranking, and Smartlead lifecycle integration.
- **Task built on it (1):** managed email-inbox infrastructure.
- **Environment notes:** external providers are mocked at their existing
  repository/service boundaries; no live email or Smartlead calls occur.

## Enterprise banking-platform - two source-minimized historical snapshots

- **Language / stack:** Groovy, Grails 2.3.11, Java 8.
- **Domain:** heterogeneous bank-statement parsing and multi-backend document
  storage.
- **Tasks built on it (2):** bank parser consolidation and Google Cloud
  Storage migration.
- **Environment notes:** these are deliberately not full repository exports.
  The parser snapshot contains only required production parser/service code
  and pinned jars. The cloud snapshot contains 23 allowlisted files. Real
  statements, test-data directories, service-account JSON, unrelated config,
  and the historical credential-bearing transfer script are excluded. The
  verifiers compile the actual production classes against synthetic fixtures
  and minimal deterministic boundary stubs.

---

## Common properties

- **Frozen and offline.** Each base image pins the repo at a fixed commit;
  task images scrub git history down to a single synthetic commit so agents
  cannot diff their way to the defects. No task needs network access, real
  credentials, or external services at solve or grade time.
- **Green or historically pre-feature.** Latent tasks begin from green code
  with planted boundary defects. Historical tasks begin at the real parent
  commit before a feature or migration. Both use gold tests injected from
  `tests/config.json` only at grade time.
- **Private substrate.** Base images and Daytona snapshots are distributed
  separately from this task repository. Publishing generated source patches
  still requires the source owner's authorization.
