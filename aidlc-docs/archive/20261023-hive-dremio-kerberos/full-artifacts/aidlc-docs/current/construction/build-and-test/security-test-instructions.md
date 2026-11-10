# Security Test Instructions — Unit 1 Foundation

## Current scope

No vulnerability scanner or penetration-test tool is configured in this repository. Security validation in this stage is limited to configuration review and the integration checks below. It does not certify production security.

## Checks

- Confirm `.runtime/` and `.env` are ignored and no generated secret values are printed or committed.
- Inspect Compose port mappings and confirm developer-facing ports bind to `127.0.0.1`; KDC, PostgreSQL, and Hive Thrift remain internal.
- Confirm only the KDC receives the KDC master password secret, only PostgreSQL receives its password secret, and Hive keytab mounts are read-only for consumers.
- Confirm the bucket initializer does not delete objects or silently treat authorization failures as a missing bucket.
- Keep RustFS root/bootstrap credential scope and Hive/RustFS per-user authorization as explicit open risks until Unit 2/3 identity provisioning and authorization scenarios are verified.

No security scan result should be inferred from a successful image build or service health check.
