# Business Rules — FreeIPA Identity Foundation

## Authority and Identity Rules

1. After accepted cutover, FreeIPA is the single authoritative directory and Kerberos KDC for `LAKEHOUSE.LOCAL`.
2. The independent MIT and FreeIPA KDC databases must not both be treated as authoritative for the same realm and principals.
3. FreeIPA owns human users, role groups, Kerberos principals, and service-account identity. RustFS policies and Ranger policies remain separately managed by their approved policy workflows.
4. Human role assignments are limited to `lakehouse-developers` and `lakehouse-analysts`; service membership uses `lakehouse-writers`. Platform `admin` privileges are separately mapped.
5. `write-service-account` is non-interactive and cannot be admitted to JupyterHub as a human user.
6. Preserve existing service-principal names where compatible. Current inventory must be rechecked before implementation; known names include `hive/hive-metastore`, `write-service-account`, `starrocks`, `kadmin/provisioner`, `admin`, `user_a`, and `user_b` in the current realm.

## Credential Rules

1. Service Kerberos keytabs, including the writer keytab, are reissued under FreeIPA as part of the approved transition.
2. The writer's RustFS S3 access key and secret remain unchanged. Kerberos keytab rotation and RustFS key rotation are independent operations.
3. Do not reuse the MIT KDC bootstrap keytab as a FreeIPA credential. Routine principal provisioning uses a separately protected, appropriately scoped FreeIPA provisioning identity.
4. Each service receives only its assigned keytab. Human notebook runtimes never receive the writer or platform administrator keytab.
5. Passwords, keytab data, ticket caches, access keys, and directory bind secrets must not appear in logs, ordinary environment values, command output, bundles, or documentation.
6. The current MIT KDC database and old service keytabs are retained as protected rollback material until cutover acceptance; they are not a steady-state second authority.

## Group and Provisioning Rules

1. FreeIPA group membership is the canonical role assignment. RustFS reconciliation and Ranger UserSync are read-side consumers.
2. Group membership changes cannot expand the policy scope defined in reviewed RustFS/Ranger policy configuration.
3. Unknown groups, unknown roles, incomplete identity lookup, or synchronization failure fail closed and produce an operator-visible, secret-safe error.
4. A grant is not considered complete until consumer synchronization and the appropriate allow/deny checks succeed.
5. A revocation is not complete until downstream access is removed and active sessions/credentials are invalidated by the responsible component workflow.
6. Account offboarding disables the FreeIPA identity before downstream cleanup; identity records, data, and workspace references are retained unless a separate approved retention process applies.

## Cutover and Rollback Rules

1. Validate FreeIPA in isolation before changing production service configuration.
2. Do not switch realm authority until principal inventory, DNS/realm compatibility, new keytabs, and dependent service updates have passed preflight.
3. Cutover is coordinated: clients must not be split across independent same-realm KDC databases.
4. A critical Hive/Spark/Airflow/StarRocks authentication failure blocks acceptance and triggers either repair before proceeding or coordinated rollback.
5. Rollback restores the previous MIT authority and corresponding old keytabs/configuration together. Do not delete data, reset volumes, or change the writer's RustFS S3 key as a rollback action.
6. Old `user_a` and `user_b` are disabled only after replacement identity and enforcement checks pass; their persisted data/workspaces are not deleted by this unit.

## Audit and Diagnostics Rules

- Record identity lifecycle events with actor, subject, action, timestamp, result, and a non-secret correlation/reference value.
- Record keytab issuance/rotation as metadata (principal, version/reference, issuer, timestamp, consumer rollout status), never key bytes.
- Authentication and reconciliation failures identify the affected principal or role and a sanitized failure category; they do not include credentials or raw ticket contents.
- Audit records do not themselves grant or revoke permissions; authorization remains enforced by the consuming component.
