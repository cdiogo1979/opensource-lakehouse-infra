# Code Generation Plan — Unit 4 Dremio Source and Query Identity

## Scope

Implement the approved Unit 4 design for Dremio local query identities, matching Hive effective usernames, and the authorization demonstration. The change stays in the existing Compose project and preserves persistent data, source configuration, service versions, proxy allowlist, and the current RustFS writer key.

The approved plan includes enabling Hive Metastore storage-based authorization using Hive's documented pre-event listener/provider settings, then treating actual RustFS path enforcement as an explicit runtime feasibility gate. No new authorization service, broad permission, administrator fallback, volume reset, or key rotation is included. User accounts remain operator-created through Dremio's UI; no undocumented account-provisioning API will be introduced.

Primary stories: US-ID-03 and US-AUTH-02. Related stories: US-AUTH-01, US-ID-02, US-CAT-01, and US-DOC-01.

## Unit Generation Context

- **Workspace**: `/Users/carlosdiogo/code_repo/hive-dremio-rustfs` (brownfield Docker Compose project).
- **Dependencies**: Completed Units 1–3; current Dremio 26.0.5 Community, Hive Metastore 3.1.3, KDC, RustFS, PostgreSQL, existing Hive source, and sample data.
- **Identity contract**: Dremio local `user_a` maps as-is to Hive effective `user_a`; Dremio local `user_b` maps as-is to Hive effective `user_b`. Dremio authenticates to Hive with its existing Kerberos service identity.
- **Acceptance matrix**: `user_a` can read `databaseA` and is denied `databaseB`; `user_b` can read both. Dremio-level, Hive-level, missing-object, and RustFS credential errors must remain distinguishable.
- **Persistence contract**: Preserve `dremio-data`, `metastore-db-data`, `object-store-data`, and `kerberos-kdc-data`; do not rerun ETL or replace Spaces/views.
- **Credential contract**: Generate distinct Dremio test-user password files under ignored, permission-restricted `.runtime/credentials/`. Preserve all existing credential files, especially the RustFS writer key. Dremio users are created manually in the supported UI.
- **Code location**: Runtime/config/scripts in the workspace root; operator and implementation documentation under `aidlc-docs/current/` and README.
- **Testing boundary**: Code Generation produces the approved config, credential bootstrap behavior, and manual query examples. Do not run runtime tests or modify persistent services in this stage; Build and Test remains a separate approval-gated stage.

## Code Generation Checklist

- [x] Map Unit 4 approved designs and stories to concrete existing files and service boundaries.
- [x] Add documented Hive Metastore storage-based authorization settings to the existing Hive template; retain effective-user and Kerberos settings.
- [x] Extend local credential bootstrap to create separate `user_a`/`user_b` Dremio password files idempotently with restrictive permissions; preserve existing files and do not touch RustFS credentials.
- [x] Add a manual Dremio user setup procedure that uses those local password files and keeps Dremio usernames aligned with Hive usernames.
- [x] Add direct-source Dremio SQL examples for the four allow/deny scenarios; identify view checks as supplemental and classify failure boundaries.
- [x] Update operator documentation with the required Hive restart/configuration step, test-user setup, redaction, state-preservation rules, and RustFS shared-credential limitation.
- [x] Add a Unit 4 implementation summary and update workflow traceability.
- [x] Reconcile all generated files against approved design; preserve the RustFS writer key and report the S3 authorization feasibility gate without changing architecture.

## Exact Planned File Changes

### Modify

- `infra/hive/hive-site.xml.in` — add the Hive Metastore pre-event authorization listener, `StorageBasedAuthorizationProvider`, explicit Hadoop metastore authenticator, and read authorization setting. Preserve current Kerberos, S3A, and `hive.metastore.execute.setugi` properties.
- `scripts/bootstrap-local.sh` — generate `dremio-user-a-password` and `dremio-user-b-password` only when absent; use random values and `0600` permissions; never print values or overwrite existing files. Do not change any RustFS credential generation or rotation behavior.
- `README.md` — document manual creation of Dremio `user_a` and `user_b`, local password-file use, Hive authorization configuration/restart, SQL checks, evidence classification, and the feasibility limit.
- `aidlc-docs/current/aidlc-state.md` and `aidlc-docs/current/audit.md` — record approved generation and completion status.

### Create

- `sql/dremio-authz-matrix.sql` — four explicit direct-source query examples with expected outcomes in comments, plus supplemental Space-view examples if useful; no credential values.
- `aidlc-docs/current/construction/unit-4-dremio/code/implementation-summary.md` — generated behavior, exact file list, operator steps, credential boundaries, non-destructive limits, and unresolved gates.

No Compose services, published ports, volumes, RustFS policy, Dremio source secret, or automatic Dremio account API integration will be added.

## Feasibility and Stop Conditions

- Hive's documented storage-based authorization configuration can be added within the approved Hive-owned authorization boundary. Its ability to distinguish identities on the current S3-compatible RustFS warehouse is not assumed.
- If the Hive authorization provider cannot initialize or requires incompatible/broad storage operations, stop the dependent runtime verification and report evidence; do not substitute a new authorization architecture without review.
- If Dremio 26.0.5 Community cannot create/authenticate the test users through its supported UI or cannot propagate the query username, report the specific blocker. Do not use admin for query tests.
- If the access matrix fails due to shared RustFS credentials or unsupported path authorization, preserve current users/data and request review of the smallest adjustment.
- Never print or commit Dremio passwords, RustFS keys, Kerberos keytabs/tickets, or credential-bearing URLs.

## References

- Apache Hive documents `hive.metastore.pre.event.listeners=org.apache.hadoop.hive.ql.security.authorization.AuthorizationPreEventListener`, `hive.security.metastore.authorization.manager=org.apache.hadoop.hive.ql.security.authorization.StorageBasedAuthorizationProvider`, and `hive.security.metastore.authenticator.manager=org.apache.hadoop.hive.ql.security.HadoopDefaultMetastoreAuthenticator` for Metastore-side storage-based authorization. Read checks are enabled by default; this does not certify S3-compatible RustFS enforcement. [Hive Storage-Based Authorization in the Metastore Server](https://hive.apache.org/docs/latest/user/storage-based-authorization-in-the-metastore-server/)

## Approval Status

**Approved by the user on 2026-10-24; code generation is complete.** The Hive template, credential bootstrap, SQL examples, and documentation are generated. No runtime configuration was rendered/applied, no accounts were created, and no tests or queries were run in this stage. All Unit 4 story acceptance outcomes remain pending Build and Test.
