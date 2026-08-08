<uploaded_files>/app</uploaded_files>

# Add S3 datastore-based usage measurement

Measurement configurations need a `"datastoreBased"` mode for S3 ingestion. Its `measurementConfiguration` contains `platform: "s3"` and the customer's string `accountId`; returned and persisted configuration also includes the generated `iamRoleArn`, `externalId`, `ingestion`, `dlq`, and `region` fields. Omitted platform and region default to `"s3"` and `"us-east-1"`. Creating a measurement must provision a uniquely named IAM role and policy scoped to that business's ingestion and DLQ prefixes, trusting the customer account with a fresh external ID. Updating the account must update role trust while preserving that role and external ID.

The internal S3 connector posts `{ message, s3Key }`, where `message` is one standard usage JSON record and the first `s3Key` segment is the business ID. Valid records must flow through the existing usage service with that business ID. Malformed records must be written to the configured DLQ under the mirrored source key plus `.message.text`, with the failed input and processing metadata; already-relative source keys must work too. Existing API-, agent-, and infrastructure-based measurement behavior must remain unchanged.

Verify with:

    cd /app && npm run build && npm run test:ci -- --runInBand
