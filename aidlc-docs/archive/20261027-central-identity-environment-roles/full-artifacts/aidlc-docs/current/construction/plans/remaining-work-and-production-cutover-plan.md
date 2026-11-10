# Production Changes and Identity Cutover Plan

## Purpose and boundary

The user chose to keep the intent open and directed that this plan cover actual production changes. Its intended outcome is a deployed FreeIPA identity authority and the approved role controls across RustFS, Spark/JupyterHub, and StarRocks native LDAP roles, followed by replacement of `user_a`/`user_b` only after the new identities pass verification. Ranger/UserSync has been removed from the target design.

This document defines execution scope, sequence, checks, and rollback. It does not itself execute the changes. Production credentials, data, policies, KDC routing, and users remain unchanged until the implementation stages and concrete cutover runbook have been reviewed and approved.

## Current baseline

- MIT KDC remains the active Kerberos authority.
- FreeIPA is validated only in the isolated validation profile/network. The current validation instance, named volume, and local Compose topology are not the production target; deploy a separately configured production service with an explicit persistent-state and backup design.
- Unit 4's FreeIPA-backed JupyterHub login and per-user Spark identities passed the recorded tests. A role-revoked pre-spawn is denied before container creation, but is currently returned to the caller as HTTP 500.
- Unit 2 has a user-accepted verification waiver for actual FreeIPA entry membership variants in the RustFS reconciler.
- Unit 3 passed with documented limits. Unit 5's StarRocks 4.1.6 native LDAP-role implementation and external Hive/Iceberg authorization have now passed on isolated services; the production FE has not been changed.
- The current RustFS reconciler is deliberately guarded to the isolated `rustfs-iam-test:9000` endpoint. Production changes require a reviewed production-capable target mode and preflight. Never weaken or remove the isolated test guard.
- The approved Unit 5 bootstrap remains guarded to the disposable FE. Do not remove that safety guard to turn it into a production tool; develop and review a separate production reconciler/migration path with an explicit target allowlist, read-only preflight, snapshot, reviewer-visible diff, and rollback.

## Work sequence

### 1. Complete implementation and verification prerequisites

Review how JupyterHub reports a `pre_spawn_hook` role mismatch. If it can be safely translated to a clear authorization-denied response, implement it and rerun allowed login/spawn, role removal with an existing session, fresh spawn denial, no-container assertion, and membership restoration. Retain fail-closed behavior if the framework cannot provide a clean status without weakening the gate. The existing test already proves no notebook is created.

### 2. Unit 5 — StarRocks native LDAP role verification

This prerequisite is complete on isolated services. StarRocks 4.1.6 native roles mapped through the FreeIPA LDAP Group Provider passed source and materialized-view access matrices, including an external Hive/Iceberg catalog. Ranger and UserSync are not part of the target. See `construction/plans/unit-5-build-and-test-plan.md` and `deploy/deployment-handoff.md`.

Before production use, prepare a separate production migration path. The isolated bootstrap is intentionally restricted to the disposable FE. Inventory current production users, roles, default roles, grants, catalogs, and ownership; identify conflicts and privilege expansion; produce an exact SQL diff and rollback. In particular, the approved direct role for `write-service-account` persists after LDAP group removal. Define account disable, session termination, direct-role revocation, and default-role reset as one offboarding operation. Do not treat FreeIPA disable alone as revoking active SQL sessions.

Acceptance for the production migration includes reviewed positive/negative SQL probes for each role, grant readback, LDAP group change behavior, audit evidence, and an independently verified RustFS boundary for direct Spark access. Use synthetic test rows and probe data only; no production data fixtures.

### 3. Decide whether to close Unit 2/3 residuals or retain their limits

The accepted Unit 2 waiver remains valid unless the user chooses to reopen it. If reopened, use a separately approved disposable FreeIPA test identity/group to exercise actual LDAP membership variants against the RustFS reconciler; retain its `rustfs-iam-test:9000` endpoint guard.

For Unit 3, first confirm which recorded limits are requirements: Hive metadata DDL authorization, group-removal-to-RustFS-revocation timing, metadata cache behavior, and Airflow DAG integration. The Unit 3 design explicitly uses RustFS as the direct Spark data boundary and does not claim that Hive metadata visibility is an authorization boundary. User-reported UAT/production DAG success is evidence for those runs, not for all worker lifecycle/recovery cases.

### 4. Production readiness inventory and preservation baseline

Capture a sanitized, read-only baseline before changing production state:

- MIT realm, principal names, current KDC aliases/DNS, keytab file ownership and consumers; record metadata and checksums without copying keytab contents into reports.
- Hive Metastore, Spark, Airflow, JupyterHub, StarRocks, and other Kerberos consumers, their service principals, config paths, trust roots, and restart requirements.
- RustFS IAM users/groups/policies/bucket settings; current role bindings; object counts and metadata-only inventory for `lake`, `lake-dev`, and `lake-uat`. Preserve all objects and the existing `write-service-account` S3 access key.
- Existing FreeIPA validation state, protected local secrets, JupyterHub named volumes, and current operational access paths.

Store protected backups outside Git. Verify restore in isolated copies before production changes.

### 5. Deploy and populate production FreeIPA

Create a dedicated production FreeIPA service, DNS/FQDN, certificates, networks, persistent storage, backup/restore, monitoring, and administrator recovery path. Do not promote the current validation container or volume by renaming it. Confirm realm/domain `LAKEHOUSE.LOCAL` and directory suffixes before initialization.

Create approved role groups and human accounts: `developer-user`, `analyst-user`, and a distinct `administrator`. Keep `write-service-account` as a service identity, not an interactive human account. Create required service principals and issue new service keytabs under FreeIPA using the approved service inventory. Securely distribute and validate each keytab. Keep the current MIT database and original keytabs preserved and untouched for rollback.

FreeIPA's documented migration design is for IPA-to-IPA migration and lists `krbprincipalkey` among skipped attributes; it does not establish a direct MIT-KDC-to-FreeIPA database migration path. Do not import the MIT database with an IPA migration utility or assume existing key material transfers. Recreate principals/keytabs and define human password transition explicitly. See the [FreeIPA migration design](https://freeipa.readthedocs.io/en/stable/designs/ipa_to_ipa_migration.html).

### 6. Apply production role policies without touching data

Develop and review production-capable reconciler configuration while preserving the test endpoint guard. Require an explicit production target, exact endpoint allowlist, complete read-only preflight, protected before-state snapshot, reviewer-visible diff, and deny-by-default behavior. Run first in read-only/dry-run mode against production IAM and compare with the approved matrix.

After a separately approved change window, reconcile only the intended IAM users/groups/policies:

| Identity | `lake` | `lake-dev` | `lake-uat` |
|---|---|---|---|
| `developer-user` | Read | Read/write | Read |
| `analyst-user` | Read | Deny | Deny |
| `write-service-account` | Read/write | Read/write | Read/write |
| administrator | Existing admin privilege | Existing admin privilege | Existing admin privilege |

Preserve all S3 objects, the current writer access key, and existing admin access. Do not run object deletion, bucket recreation, or data migration as part of IAM policy application. Verify exact policy readback and positive/negative S3 probes using synthetic nonce objects, then delete only those exact probes.

### 7. Connect production consumers in a controlled order

Use staged changes with health checks after each service, retaining MIT as the active authority until the actual authority transition window:

1. Verify FreeIPA DNS, TLS, LDAP role lookup, KDC ticket issuance, and account lock behavior from authorized internal clients.
2. Configure the Hive Metastore service principal/keytab and validate Hive SASL plus read/write access to its current RustFS objects.
3. Configure Spark/Airflow service principal/keytab to the FreeIPA-issued `write-service-account` identity while preserving its RustFS S3 access key and the existing production/UAT DAG bundle list. Run the approved UAT workload and verify table/object checksums, schema, and location; do not let ETL create a second broad credential path.
4. Configure JupyterHub to the production FreeIPA LDAPS endpoint and production CA. Verify all role logins, per-user mounts, S3/Spark authorization, role revocation, ticket destruction, and persistent workspace isolation.
5. Configure StarRocks native LDAP authentication and its LDAP Group Provider against production FreeIPA; register approved LDAP users bound to their FreeIPA DNs, install the reviewed role/grant set, and verify SQL authorization and audit records. Ranger services/plugins are not deployed. Confirm direct Spark remains protected independently by RustFS IAM.

### 8. Rehearse and execute the MIT authority transition

Before production transition, rehearse the sequence and rollback against isolated copies. The runbook must define how the active MIT authority is fenced and how FreeIPA becomes the sole authority for the same realm without split-brain KDC behavior. Do not run two independent KDC databases as simultaneous authorities for `LAKEHOUSE.LOCAL` unless an explicitly supported and tested replication/transition mechanism is designed.

During a separately approved maintenance window:

1. Freeze identity, password, role, and policy changes; snapshot MIT KDC state and verify protected recovery copies.
2. Confirm production FreeIPA readiness and all required principals/keytabs; confirm every client can be switched and restarted.
3. Fence MIT issuance at the documented transition point; activate FreeIPA as the sole KDC authority and update the approved KDC discovery/configuration path.
4. Move a canary through ticket acquisition, Hive access, S3 role checks, Spark SQL, JupyterHub, Airflow, and StarRocks native LDAP roles.
5. Continue client migration in the approved order only after each gate passes. Keep old identities and protected MIT rollback artifacts until the acceptance window closes.
6. Disable `user_a` and `user_b` only after the replacement identities pass all positive and negative probes. Preserve their data and workspaces; do not delete their identities as a default cleanup action.

### 9. Rollback triggers and procedure

Stop and roll back if a denied operation succeeds, an approved role is broader than the matrix, any service cannot obtain/use its expected ticket, a required production data read differs, JupyterHub exposes cross-user material, or the backup/restore checkpoint is invalid.

Rollback must restore the single prior KDC authority, client configuration/DNS discovery, original protected keytabs, and service availability as one coordinated change. Restore the recorded RustFS IAM state only if the reviewed diff changed managed policy; never restore or overwrite object data as an IAM rollback. Restore prior JupyterHub service configuration while preserving user workspace volumes. Record service outcomes and verify old and new login paths explicitly. Do not delete either KDC's persistent state during rollback.


## Decision gates

1. Production-change plan and Unit 5 isolated design/build/test are complete; Ranger/UserSync was removed from scope.
2. Decide whether to reopen the Unit 2 waiver and which Unit 3 limits remain requirements.
3. Review the sanitized production StarRocks grant/catalog inventory and approve the exact native-role migration diff, writer offboarding procedure, and rollback.
4. Approve the production FreeIPA target, RustFS production reconciler mode, consumer changes, backup/restore, and integrated rollback runbook.
5. Approve the exact production maintenance window and change list before IAM policies, accounts, client configuration, keytabs, or KDC routing changes.

## Read-only production StarRocks inventory — 2026-10-28

The user approved continuation to the planned read-only inventory. The production FE was queried only with `SHOW USERS`, `SHOW ROLES`, `SHOW CATALOGS`, `SHOW DATABASES`, and `SHOW GRANTS`; no credentials were displayed, no table contents were selected, and no SQL mutation was issued.

- Users present: `root`, `admin`, `user_a`, `user_b`, and `write_service_account`. The legacy user accounts are still present and must remain until replacement identities pass cutover verification.
- Catalogs: `default_catalog` (internal) and `iceberg` (external Iceberg catalog).
- Roles: StarRocks built-ins `root`, `db_admin`, `cluster_admin`, `user_admin`, `public`, and `security_admin`. The built-in `public` role has `SELECT` on `information_schema` only.
- `root` has the built-in `root` role. `admin` is assigned `db_admin`, `cluster_admin`, `user_admin`, and `security_admin`.
- `user_a` has `SELECT` on all tables in `iceberg.databaseA` plus catalog `USAGE`.
- `user_b` has `SELECT` on all tables in `iceberg.databaseA` and `iceberg.databaseB` plus catalog `USAGE`.
- `write_service_account` has `SELECT` on all tables in both databases and direct `INSERT`, `UPDATE`, and `DELETE` grants on the eight currently listed tables in each database, plus catalog `USAGE`. Those eight table names are `customer`, `lineitem`, `nation`, `orders`, `part`, `partsupp`, `region`, and `supplier`.
- External-catalog database listing also includes `aidlc_u3_20261027_dev`, `aidlc_u3_20261027_prod`, `aidlc_u3_20261027_uat`, `default`, `default_lh`, and `default_lhuat`, in addition to `databasea` and `databaseb` and system metadata databases. These are names only; no table data or object contents were read. `default_lhdev` was not present in the external catalog listing.

**Migration implications**: Existing `user_a`/`user_b` access is direct-user grants, not the new FreeIPA group-derived roles. The user selected preservation of the writer's direct source DML grant scope. Preserve the exact table-scoped privileges through migration; do not expand to all current or future tables. Also reconcile `aidlc_u3_*` and legacy databases only if they are explicitly in the production scope; do not remove them as cleanup.

Read-only login checks showed `CURRENT_ROLE()` is `NONE` for `user_a`, `user_b`, and `write_service_account`; `admin` activates `db_admin`, `cluster_admin`, `user_admin`, and `security_admin`; `root` activates `root`. The global `activate_all_roles_on_login` setting is `false`. A `SHOW CREATE USER` attempt is not supported by the running FE; account role activation was instead verified from these read-only account logins. No grant, user, role, catalog, database, table, or production data was changed.

### Writer DML decision and isolated Iceberg behavior

The user chose to preserve existing writer grants: `INSERT`, `UPDATE`, and `DELETE` on the eight inventoried tables (`customer`, `lineitem`, `nation`, `orders`, `part`, `partsupp`, `region`, `supplier`) in each of `iceberg.databaseA` and `iceberg.databaseB`, in addition to the existing SELECT and catalog USAGE. Carry that exact privilege set into the new writer group role as a reviewed table-scoped migration; preserve the direct `lakehouse_writer` exception required for asynchronous materialized-view refresh. Do not broaden the scope or remove the old direct grants until the production replacement passes separately approved acceptance checks.

An isolated StarRocks 4.1.6 external Iceberg table test, using a synthetic database/table and isolated Hive Metastore/RustFS services, found:

- `INSERT` succeeded.
- `DELETE` succeeded, and readback confirmed only the requested synthetic row was removed.
- `UPDATE` was rejected as unsupported by the StarRocks Iceberg connector.

Therefore, retaining UPDATE preserves the existing grant metadata as the user requested, but does not make UPDATE executable against external Iceberg on this StarRocks version. Any workload needing row changes must use supported DELETE plus INSERT or a separately reviewed rewrite method. Do not claim UPDATE behavior was verified or functional. The test writer authenticated over TLS with `CURRENT_ROLE() = lakehouse_writer`; the readback showed the DELETE and INSERT results. The disposable catalog and synthetic records, its isolated services and volumes, and generated test credentials were removed. Production was not connected to that test.

### Draft writer-role migration SQL (review only; not applied)

StarRocks requires `SET CATALOG` before external-catalog table grants. Use the existing table names from the read-only inventory; this draft does not include any new table and does not change the current user grants.

```sql
CREATE ROLE IF NOT EXISTS lakehouse_writer;
GRANT USAGE ON CATALOG iceberg TO ROLE lakehouse_writer;
SET CATALOG iceberg;
GRANT SELECT ON ALL TABLES IN DATABASE databaseA TO ROLE lakehouse_writer;
GRANT SELECT ON ALL TABLES IN DATABASE databaseB TO ROLE lakehouse_writer;
GRANT INSERT, UPDATE, DELETE ON TABLE
  databaseA.customer, databaseA.lineitem, databaseA.nation, databaseA.orders,
  databaseA.part, databaseA.partsupp, databaseA.region, databaseA.supplier
  TO ROLE lakehouse_writer;
GRANT INSERT, UPDATE, DELETE ON TABLE
  databaseB.customer, databaseB.lineitem, databaseB.nation, databaseB.orders,
  databaseB.part, databaseB.partsupp, databaseB.region, databaseB.supplier
  TO ROLE lakehouse_writer;
GRANT lakehouse_writer TO EXTERNAL GROUP lakehouse-writers;
GRANT lakehouse_writer TO USER 'write_service_account'@'%';
```

The `SELECT ON ALL TABLES` grants preserve the inventoried read scope across both databases. The table-specific DML grants preserve only the eight inventoried table privileges in each database. The external-group grant maps the FreeIPA writer group; the direct user-role grant retains the tested asynchronous MV refresh exception. The UPDATE privilege is retained as requested but does not make Iceberg UPDATE work on StarRocks 4.1.6.

Before any application, check that the FE reports the expected version/catalog/database/table identities; capture all role/user grants and active-role behavior; verify the LDAP external group resolves to the intended FreeIPA group; and run these statements in a reviewed transaction window with an immediate post-change `SHOW GRANTS` and positive/negative probes. Keep the old direct grants during this additive role bootstrap. Remove them only in a separately reviewed cleanup after the group-role path passes acceptance.

Rollback for this additive draft is to revoke the new role grants and assignments, then drop the new role only if it did not exist before the change:

```sql
REVOKE lakehouse_writer FROM USER 'write_service_account'@'%';
REVOKE lakehouse_writer FROM EXTERNAL GROUP lakehouse-writers;
SET CATALOG iceberg;
REVOKE SELECT ON ALL TABLES IN DATABASE databaseA FROM ROLE lakehouse_writer;
REVOKE SELECT ON ALL TABLES IN DATABASE databaseB FROM ROLE lakehouse_writer;
REVOKE INSERT, UPDATE, DELETE ON TABLE
  databaseA.customer, databaseA.lineitem, databaseA.nation, databaseA.orders,
  databaseA.part, databaseA.partsupp, databaseA.region, databaseA.supplier
  FROM ROLE lakehouse_writer;
REVOKE INSERT, UPDATE, DELETE ON TABLE
  databaseB.customer, databaseB.lineitem, databaseB.nation, databaseB.orders,
  databaseB.part, databaseB.partsupp, databaseB.region, databaseB.supplier
  FROM ROLE lakehouse_writer;
DROP ROLE lakehouse_writer;
```

This rollback is a draft, not a runbook for blind execution. If the role existed before rollout, preserve it and revoke only the grants/assignments introduced by this change. Do not remove the old direct grants as part of either additive application or rollback.

### Production writer-role preflight — 2026-10-28

The user approved applying the additive writer-role SQL above, subject to a production preflight. The read-only preflight targeted `iceberg-poc-starrocks-fe` and confirmed:

- `SHOW FRONTENDS` reports FE version `4.1.6-6862092` and a healthy LEADER.
- The `iceberg` external catalog exists; `databaseA` and `databaseB` each contain all eight inventoried tables.
- The `write_service_account` grant readback matches the planned SELECT, table-scoped INSERT/UPDATE/DELETE, and catalog USAGE scope.
- `SHOW GROUP PROVIDERS` returns no rows, and `SHOW ROLES` lists only built-in roles; `lakehouse_writer` does not yet exist.
- Docker metadata shows the production FE only on `iceberg-poc-net`. The only running FreeIPA is `iceberg-poc-freeipa-validation`, attached to `iceberg-poc-freeipa-validation-net` and `iceberg-poc-jupyterhub-ipa-net`; the FE has no shared network path to it. JupyterHub can reach the validation service, but that does not make it a production StarRocks directory endpoint.

**Outcome: no production SQL was applied.** The missing group provider is a prerequisite failure for the reviewed two-principal assignment: `GRANT lakehouse_writer TO EXTERNAL GROUP lakehouse-writers` would not establish an effective FreeIPA group mapping without the production LDAP Group Provider and associated authentication integration. This preflight made no user, role, grant, catalog, database, table, or data changes. The current direct writer grants remain intact.

Before retrying, configure and verify the production StarRocks LDAP Group Provider and LDAP authentication integration against the approved production FreeIPA endpoint, then rerun the read-only preflight and apply the same additive SQL only after the external group resolves. This requires its own reviewed production configuration/change plan; the isolated FreeIPA validation service is not the production identity authority. Keep all existing direct grants until the group-derived path passes the approved positive and negative checks.

### Dedicated production FreeIPA integration selection — 2026-10-28

The user chose the dedicated production FreeIPA option; the isolated `iceberg-poc-freeipa-validation` instance is not to be promoted or connected to the StarRocks FE. Prepare a separate production deployment path with these defaults:

- Use a distinct stable FQDN such as `ipa-prod.lakehouse.local`, with the approved realm/domain `LAKEHOUSE.LOCAL` / `lakehouse.local`. Do not reuse the validation FQDN or its data volume.
- Keep the new service in an explicit Compose profile and a dedicated internal network shared only by production FreeIPA and the StarRocks FE for LDAPS. Do not publish LDAP, Kerberos, or DNS ports to the host; publish an admin UI only to loopback if needed.
- Use a new named persistent volume and separate production installer/admin/LDAP-reader credentials. Mount only the FreeIPA public CA and a dedicated read-only group-search bind credential into StarRocks. Keep those secrets out of Compose environment values, SQL histories, logs, and Git.
- Configure the FE's native LDAP simple-bind host, port, user DN pattern, CA trust path, and `group_provider` persistently. The production FE entrypoint currently persists only `group_provider`; it does not yet have the LDAP authentication host/TLS settings or a trust-store mount.
- Require TLS on the StarRocks MySQL protocol before enabling LDAP SQL logins. The disposable FE has a test-only Java keystore and TLS configuration; the existing production FE configuration does not yet have equivalent production key material or SQL-client CA distribution. Generate a separate FE certificate/keystore and provide its CA to SQL clients before testing LDAP logins.
- Initially leave the existing MIT KDC and all current clients unchanged. FreeIPA includes a KDC, so the new KDC must not be advertised to or used by general clients before the separately rehearsed authority transition. No keytab reissuance, MIT fencing, user retirement, or RustFS policy changes are part of the StarRocks LDAP provider bootstrap.
- Add the LDAP Group Provider and its cluster-wide `group_provider` setting through a separate production-specific reconciler with exact FE container identity checks, dry-run diff, protected secrets, immediate metadata readback, and rollback. Do not relax the existing disposable-FE guard in `bootstrap_roles.py`.

This is the approved deployment direction, not a completed deployment. The optional production FreeIPA Compose profile, FE LDAP/TLS configuration, protected certificate/installer helpers, and production-only guarded group-provider preflight/apply tool are now prepared as a reviewable draft. The dedicated reader identity, backup/restore rehearsal, grant migration, and live deployment remain open. Review the full diff before starting FreeIPA or recreating the FE, since the FE network/config change requires a planned restart. No production FreeIPA service, FE network, LDAP provider, role, or grant has been changed by this work.

### Optional production FreeIPA / StarRocks integration draft — 2026-10-28

Prepared an isolated, opt-in configuration for review; it has not been started or applied:

- `docker-compose.freeipa-production.yml` adds the `freeipa-production` profile, dedicated hostname/IP (`ipa-prod.lakehouse.local` / `172.31.250.10`), private internal network, named state volume, and loopback-only HTTPS UI on port 8444. It does not publish LDAP, Kerberos, or DNS ports. The production FE override adds only the LDAP network path, LDAPS settings, CA mount, and StarRocks SQL TLS materials; the base Compose file and validation instance remain separate.
- `scripts/prepare-freeipa-production-secrets.sh` prepares unique protected installer/admin/LDAP-reader credential files and installer options without displaying values. `scripts/export-freeipa-production-ca.sh` exports and validates only the dedicated production CA. `scripts/prepare-starrocks-production-tls.sh` prepares a separate StarRocks SQL JKS and public certificate using the pinned local FE image.
- `infra/starrocks/fe/entrypoint.sh` enables LDAP auth and TLS only when the production override supplies `STARROCKS_LDAP_SERVER_HOST`, and fails closed if the approved host/port/DN pattern or CA/keystore/password files are invalid. The production override uses LDAPS with CA validation and forces secure SQL transport.
- `infra/freeipa/patch-httpd-redirects.py` now accepts a configured UI port so the dedicated server can redirect to its loopback-published 8444 endpoint without changing the validation server’s 8443 default.

The separate provider reconciler is now prepared at `scripts/bootstrap-starrocks-production-group-provider.py`; it does not alter or bypass the disposable-FE bootstrap guard. Its default mode performs guarded, read-only production preflight and refuses if another provider exists; `--apply` creates only the missing provider and reads it back. It does not create users/groups/roles or issue grants. Backup/restore rehearsal, production identity seeding, and deployment are **not included or executed**. The prepared secret helper creates a password for `starrocks-ldap-reader`, but the matching FreeIPA user and narrowly scoped read access still need a separately reviewed production provisioning step. No StarRocks SQL has been sent to the live FE.

One identity binding must be settled before any production user/role migration: the existing StarRocks account inventoried as `write_service_account` uses an underscore, while the FreeIPA role identity approved in the policy is `write-service-account` with hyphens. The isolated bootstrap registers `write-service-account` as an LDAP login but separately grants its direct writer role to that hyphenated SQL user; that does not establish that the existing underscore account is the same authenticated principal. **Recommendation:** keep the FreeIPA UID `write-service-account`, register that exact LDAP username in StarRocks, and treat the existing underscore account as a distinct legacy identity until its grants/session ownership are verified; do not copy direct grants or passwords between the two names. The new provider preflight reports whether each account exists, but a read-only production auth/grant/session inventory must resolve the binding before migrating roles or grants.

Before deployment, review the complete compose/config/script diff, select and check the private subnet against the actual Docker host routes/networks, establish a protected backup/restore path for the new FreeIPA state, and confirm local secret-path ownership is readable by the root-run FE and FreeIPA containers. The JKS certificate is self-signed; distribute its public `.crt` to authorized SQL clients and require CA verification. Verify the generated StarRocks TLS config and LDAP settings against the exact 4.1.6 build in an isolated clone before the live FE restart.

Suggested staged sequence after explicit deployment approval:

1. Prepare protected files with `./scripts/prepare-freeipa-production-secrets.sh`; inspect only file names, ownership, and modes, never their contents.
2. Start only the new directory with `docker compose -f docker-compose.yml -f docker-compose.freeipa-production.yml --profile freeipa-production up -d freeipa-production`. Do not start or restart StarRocks in this step. Provision production identities/groups and the dedicated `starrocks-ldap-reader` using a separately reviewed procedure; verify LDAPS certificate, group contents, backups, and restore before proceeding.
3. Export the dedicated public CA with `./scripts/export-freeipa-production-ca.sh`, prepare FE SQL TLS with `./scripts/prepare-starrocks-production-tls.sh`, and securely distribute the public certificate to SQL clients.
4. Before an approved FE maintenance window, capture the production metadata/grant snapshot and verify rollback prerequisites. Then restart only the FE with `docker compose -f docker-compose.yml -f docker-compose.freeipa-production.yml --profile starrocks --profile freeipa-production up -d starrocks-fe`. Check FE health, MySQL TLS, LDAP authentication, CA verification, and group resolution before role grants.
5. Run the provider reconciler in read-only mode with the exact Compose project label, inspect its status output, and resolve the underscore/hyphen writer identity before any grant migration. After review, apply only the missing provider with `scripts/bootstrap-starrocks-production-group-provider.py --compose-project <exact-compose-project> --apply`; read it back and verify LDAP group membership and fail-closed negative cases. Only then apply the previously approved additive writer-role grants using a separate production migration.
6. Roll back by recreating only the FE from the base Compose file with `docker compose -f docker-compose.yml --profile starrocks up -d --no-deps starrocks-fe`. Preserve the StarRocks metadata volume and the dedicated FreeIPA volume for investigation/recovery. If the provider or grants were added, revoke only the objects and assignments created by this migration after taking a before/after readback; retain all existing direct writer grants and data. Do not delete either volume as rollback.

No Docker services, networks, volumes, production users, provider, roles, grants, catalog objects, or data were changed while preparing this draft. No tests or runtime validations were run in this step.

## Exit criteria for the intent

The intent can close with a clearly recorded waiver if the user chooses to stop before production rollout. To claim completed production centralization, the production FreeIPA authority and role policies must be active; all approved consumers must pass the integrated role matrix; old identities must be retired only after replacement verification; backups, preservation, and rollback must be demonstrated; and the authority transition must be explicitly approved and recorded.
