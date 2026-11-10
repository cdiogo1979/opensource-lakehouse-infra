# Unit of Work — Central Identity and Environment Access

## Decomposition principles

Keep identity lifecycle, storage enforcement, human notebook credentials, analytical query authorization, and cutover independently reviewable. StarRocks native roles govern SQL through StarRocks; RustFS IAM independently governs direct Spark object access. Units preserve current production objects and the writer's RustFS S3 key; service Kerberos keytabs are reissued under FreeIPA.

## Unit 1 — FreeIPA Identity Foundation

**Outcome**: FreeIPA is ready as the directory and Kerberos authority, with human role groups and the required service identities.

**Scope**: FreeIPA service/configuration; realm and DNS integration; groups `lakehouse-developers`, `lakehouse-analysts`, `lakehouse-writers`; administrator separation; service principals and protected provisioning.

**Stories**: US-01, US-08, US-11.

**Exit contract**: LDAP/TLS lookup and authentication work; principals and group membership resolve; FreeIPA-issued Kerberos service tickets and replacement keytabs for HMS/Spark and existing services are verified before staged MIT-KDC replacement. Old KDC/keytabs remain rollback-only until acceptance.

**Dependencies**: Existing realm and current principal/keytab inventory.

## Unit 2 — Declarative RustFS Role Policies and Reconciliation

**Outcome**: FreeIPA memberships map idempotently to exact RustFS permissions across `lake`, `lake-dev`, and `lake-uat`.

**Scope**: Version-controlled role policy document; RustFS IAM user/group/policy reconciler; per-user key lifecycle; bucket creation; drift checks; safe error reporting; positive and negative S3 probes.

**Stories**: US-02, US-03, US-04, US-05, US-06, US-07.

**Exit contract**: Effective permissions match the approved matrix, cross-environment writes are denied as required, new buckets are preserved/idempotent, the writer's RustFS S3 key and production objects remain intact, and FreeIPA service keytabs are validated.

**Dependencies**: Unit 1 directory/group contract; RustFS pinned-version capabilities.

## Unit 4 — Per-User Notebook and Spark Identity

**Outcome**: JupyterHub users authenticate against FreeIPA and their Spark sessions use only the user's own Kerberos and RustFS identities.

**Scope**: LDAP/TLS authenticator; group-based spawn authorization; isolated credential material mounts; per-user Kerberos ticket cache lifecycle; revoke-and-stop workflow; service identity exclusion.

**Stories**: US-08, US-09.

**Exit contract**: Positive and negative Spark/HMS/S3 tests prove role-based data access; cross-environment database/table metadata visibility is accepted, but unauthorized object reads/writes fail at RustFS. No cross-user credential visibility; no shared writer credentials in notebook containers; user revocation terminates sessions and denies subsequent requests.

**Dependencies**: Units 1–3; JupyterHub Docker spawner and secret-mount capabilities.

## Unit 3 — Hive Metastore and Database Authorization

**Outcome**: Direct Spark clients use the correct database-to-bucket mapping and RustFS-enforced object role scope. Cross-environment database/table metadata visibility is accepted.

**Scope**: Kerberos identity mapping; explicit database locations; per-user RustFS credentials for direct Spark; allow/deny behavior for database/table data reads and object writes. Metadata DDL restrictions are not guaranteed by the current Hive/S3A setup and require a separate authorization design if needed.

**Stories**: US-03, US-04, US-05, US-06, US-09.

**Exit contract**: Analyst reads production data and receives RustFS denial on dev/UAT; developer reads all and writes only dev; writer reads/writes all buckets. Spark probes use each role's own RustFS identity with no writer fallback. Metadata visibility may span environments. If analyst metadata DDL must be denied, stop and raise a separate architecture change.

**Dependencies**: Units 1 and 2.

## Unit 5 — StarRocks LDAP Group Roles

**Outcome**: StarRocks queries use native StarRocks roles mapped to FreeIPA LDAP groups, while its service identity accesses HMS/RustFS data.

**Scope**: StarRocks LDAP authentication and group provider; explicit LDAP user registrations; native roles/grants mapped to FreeIPA external groups; external Hive catalog access.

**Stories**: US-10.

**Exit contract**: Version compatibility is established; role-matrix allow/deny queries pass; direct Spark authorization remains separately enforced by Units 2–4.

**Dependencies**: Unit 1 groups, StarRocks 4.1.6 LDAP/native RBAC support, and Unit 2 storage identities.

## Unit 6 — Safe Identity Cutover and Integrated Verification

**Outcome**: Replace `user_a`/`user_b` with the approved role identities without losing data, writer access, or platform administration.

**Scope**: Preflight, staged verification, old-user revocation, rollback path, preservation checks, integrated role-matrix evidence.

**Stories**: US-02, US-07, US-11.

**Exit contract**: All acceptance criteria pass before old identities are disabled; production objects and Jupyter workspaces are retained; `admin` and writer remain functional.

**Dependencies**: Units 1–5.

## Cross-unit constraints

- Keep native StarRocks SQL enforcement distinct from direct Spark-to-RustFS access.
- Do not add HiveServer2 unless Unit 4 proves a required metastore/S3A boundary is unsupported and the user approves the architecture change.
- Never mount the broad ETL writer secret into a human notebook runtime.
- No construction starts until the design and this decomposition are explicitly approved.
