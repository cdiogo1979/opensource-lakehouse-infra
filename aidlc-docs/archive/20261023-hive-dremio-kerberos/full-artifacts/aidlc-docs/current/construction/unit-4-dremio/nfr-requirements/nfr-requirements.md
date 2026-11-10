# Unit 4 NFR Requirements — Dremio Source and Query Identity

These requirements apply to the per-user Dremio authorization demonstration in the existing single-host Compose PoC. They preserve the approved functional matrix and do not introduce production service objectives.

## Performance and scale

- **U4-NFR-01**: Support the fixed demonstration scope of two query users, the existing two Hive databases, and the current sample tables/views. Run allow/deny checks serially for clear identity and failure attribution.
- **U4-NFR-02**: No query latency, throughput, concurrency, or horizontal-scale SLA is required. A query is considered successful when it returns the expected result within the operator's execution window and the effective identity/outcome can be recorded.

## Availability and recovery

- **U4-NFR-03**: The environment is single-host, best effort, and manually recoverable. No HA, failover, uptime, or disaster-recovery objective is required.
- **U4-NFR-04**: A failed authorization scenario must not trigger volume reset, sample-data deletion, or unrelated ETL reruns. Preserve existing state and rerun only failed non-destructive query checks after correcting a diagnosed transient/precondition issue.
- **U4-NFR-05**: Service health and source connectivity are preconditions only; they do not establish per-user authorization correctness.

## Security and evidence

- **U4-NFR-06**: Authenticate `user_a` and `user_b` with distinct Dremio local accounts and distinct randomly generated Dremio passwords. Store any generated passwords only in ignored, permission-restricted `.runtime/credentials/` files. Do not reuse Kerberos passwords/keytabs or RustFS keys as Dremio passwords.
- **U4-NFR-07**: Continue using the dedicated Dremio Kerberos service identity for the Hive connection. Preserve the current bounded proxy-user rules. Do not rotate or replace the RustFS writer key during Unit 4.
- **U4-NFR-08**: Record only the minimum redacted scenario results and log excerpts needed to identify the Dremio user, effective Hive user, target database/table, outcome, and decision component. Keep evidence local; no formal retention period or separate audit service is required.
- **U4-NFR-09**: Never include passwords, S3 access/secret keys, keytab contents, Kerberos ticket contents, authorization headers, or credential-bearing URLs in logs, manifests, or workflow documentation.
- **U4-NFR-10**: A denied query counts as authorization evidence only if the expected effective Hive identity is observable and the denial is attributable to Hive authorization. Dremio authentication, source/Space permissions, missing objects, and S3 credential failures must be classified separately.
- **U4-NFR-11**: Do not claim RustFS per-user authorization from successful access through the Dremio source's shared S3 credentials.

## Compatibility and maintainability

- **U4-NFR-12**: Preserve the pinned Dremio 26.0.5 Community, Hive Metastore 3.1.3, Kerberos realm, and Compose service boundaries. Any version or architecture change requires separate review if the approved behavior cannot be met.
- **U4-NFR-13**: Keep the authorization test repeatable and non-destructive, with one result record per user/database scenario and explicit expected-versus-actual outcome.
- **U4-NFR-14**: Treat missing Hive storage-based authorization configuration or inability to enforce the required matrix over RustFS as an explicit feasibility blocker. Preserve existing credentials/data and present the smallest proposed adjustment for review; do not silently weaken access criteria or grant administrator privileges.

## Assessment status

The user's answers confirm the fixed PoC scale, manual recovery, local redacted evidence without formal retention, and separate local Dremio accounts. These are requirements only; they do not assert that the matrix has passed or authorize runtime changes.
