# Deployment Handoff — Central Identity and Environment Roles

## Status

**Units 4 and 5 Build and Test are complete in the isolated validation setup. Production deployment and MIT KDC authority cutover have not occurred.** The MIT KDC remains authoritative. FreeIPA remains isolated on its validation network.

This handoff summarizes the tested implementation and records the limits that must remain visible in any rollout decision.

## Validated behavior

- FreeIPA LDAPS authenticates `developer-user`, `analyst-user`, and `administrator`; role checks fail closed for missing, locked, conflicting, writer-only, service, invalid, and legacy `user_a`/`user_b` accounts.
- JupyterHub maps each allowed human to only that identity's read-only keytab and RustFS credential files, ticket cache, and persistent workspace. Notebook processes run as UID/GID 10001.
- Spark access uses the matching user's RustFS identity. Hadoop UGI must also be initialized from the staged keytab with `UserGroupInformation.loginUserFromKeytab`; native `kinit`/`klist` alone did not establish a JVM Subject for Hive SASL.
- Direct notebook S3 probes matched the approved matrix. A synthetic Iceberg table was created and queried by developer, denied to analyst, and read by administrator; the table namespace and test objects were removed.
- LDAP outage and missing Hub secrets deny access/startup. Invalid CA and hostname mismatch were denied. A missing CA bind source prevents container creation.
- The JupyterHub admin API stopped the administrator notebook (HTTP 204). One-use API tokens were revoked and verified unauthorized (HTTP 403); no CLI-generated token records remained.
- With a developer's role temporarily removed, a fresh spawn from the existing session was denied and no notebook was created. The membership was restored.

See [Unit 4 Build and Test](../construction/plans/unit-4-build-and-test-plan.md) for detailed evidence.

## Known behavior and verification limits

- An expected role mismatch in JupyterHub's pre-spawn hook currently appears as HTTP 500, even though the denial happens before any notebook is created. Consider improving the user-facing error before broad rollout.
- Unit 2 Build and Test has a user-accepted verification waiver: actual FreeIPA-entry membership variants were not exercised. The RustFS reconciliation and role probes were exercised on the isolated test service.
- Unit 3 passed with documented limits: analyst Hive metadata DDL authorization, FreeIPA group-membership revocation timing, Hive metadata-cache behavior, and Airflow ETL integration are not established. The tested object-level boundary is RustFS authorization using each caller's own S3 credentials.
- No numeric revocation SLA was established. No production identity migration, MIT KDC cutover, or RustFS production policy edit was performed.

## Rollout boundary

The tested setup is a validation implementation, not evidence that production clients have been migrated. Do not switch the active `kdc` alias, attach production clients to the validation FreeIPA network, replace the MIT KDC, or rotate production keytabs as part of this handoff. A production rollout needs a separately reviewed cutover and rollback procedure that inventories consumers, principals, service keytabs, DNS, and recovery access.

## Evidence and cleanup

- No Jupyter notebook containers remain running; the developer, analyst, and administrator named workspace volumes remain.
- Temporary test users/passwords, probe objects, and CLI-generated API tokens were removed or revoked.
- The active MIT KDC, existing RustFS policies, and protected production data were not changed by Unit 4 verification.
- The Spark example and README describe the explicit Hadoop UGI keytab login needed for Hive SASL.

## Handoff gate

Review this evidence and the documented limitations before authorizing any production cutover. This document does not perform deployment or change the active Kerberos authority.

## Unit 5 handoff — StarRocks native LDAP roles (2026-10-28)

### Validated on isolated services

- StarRocks 4.1.6 LDAP over CA-verified TLS applied the expected FreeIPA group-derived roles. The 15-case StarRocks external Hive/Iceberg catalog matrix passed: developer reads all environments and inserts only to dev; analyst reads prod only; `write-service-account` reads and inserts all three.
- On the disposable FE, the writer created and managed materialized views in `default_lh`, `default_lhdev`, and `default_lhuat`; developer and analyst MV read boundaries passed. Negative DDL/security checks denied catalog/database administration, user/role creation, and grants.
- FreeIPA group removal after the configured cache interval removed developer/analyst access in fresh StarRocks sessions. The direct writer role is an approved exception: async MV refresh uses this direct role, so group removal does not revoke it. FreeIPA account disable blocks new logins, while a pre-existing SQL session remains usable until it is closed. Full writer retirement therefore requires closing sessions and revoking the direct StarRocks role/resetting the default role as well.
- A manual-refresh materialized view over a synthetic external Iceberg table was created and synchronously refreshed on the disposable FE. It returned the synthetic row. The single-BE test required `replication_num=1`.

See [Unit 5 Build and Test](../construction/plans/unit-5-build-and-test-plan.md) for commands/results and cleanup details. The Hive Metastore/RustFS test stack, its two named volumes, generated test credentials, synthetic catalog, and probe MV were removed. Disposable StarRocks FE/BE and isolated test FreeIPA remain. No Ranger services are required.

### Production work remains separate

- No production FE grants, catalogs, identities, RustFS policies, Hive metadata, active MIT KDC state, or data were changed. The test bootstrap remains guarded for the disposable FE and must not be pointed at production.
- Before rollout, inventory existing production FE users, default roles, grants, catalogs, and object ownership. Review collisions and define the reconciled grants and rollback before applying anything.
- Define writer-account offboarding so FreeIPA disable is followed by SQL session termination and direct-role revocation/default-role reset. Establish a numeric revocation expectation if one is required; none was specified.
- Prepare and separately review the production deployment, consumer migration, MIT KDC transition, and rollback sequence. This handoff records evidence; it does not authorize or perform those changes.

Direct Spark/RustFS enforcement remains as recorded in Unit 3 and was not re-run through the retained production-attached probe launcher. Unit 3's metadata-DDL, group-revocation timing, Hive metadata-cache, and Airflow integration limits remain open. Unit 2's actual FreeIPA membership test remains waived, and Unit 4's denied pre-spawn response still surfaces as HTTP 500.

### Production StarRocks inventory (read only, 2026-10-28)

The approved metadata-only inspection found users `root`, `admin`, `user_a`, `user_b`, and `write_service_account`; catalogs `default_catalog` and `iceberg`; and built-in roles `root`, `db_admin`, `cluster_admin`, `user_admin`, `public`, and `security_admin`. `admin` currently has four built-in administrative roles (`db_admin`, `cluster_admin`, `user_admin`, `security_admin`); `root` has the built-in `root` role. The `public` role grants `SELECT` on `information_schema` only.

`user_a` has SELECT on all tables in `iceberg.databaseA`; `user_b` has SELECT on all tables in `iceberg.databaseA` and `iceberg.databaseB`. Both also have catalog USAGE. `write_service_account` has SELECT across both databases and INSERT/UPDATE/DELETE on the eight listed tables in each: customer, lineitem, nation, orders, part, partsupp, region, supplier. These are existing direct user grants, not FreeIPA group mappings.

The external `iceberg` catalog lists `databaseA`, `databaseB`, three `aidlc_u3_20261027_*` namespaces, `default`, `default_lh`, and `default_lhuat`; `default_lhdev` was not listed there. No table contents were read. Do not infer from the listing that the internal `default_catalog` lacks its designed MV databases. Retain legacy grants and namespaces until an approved migration specifically reconciles them.

The user chose to preserve the current writer `INSERT`/`UPDATE`/`DELETE` grant scope. An isolated StarRocks 4.1.6 test against a synthetic external Iceberg table confirmed `INSERT` and `DELETE`; `UPDATE` was rejected as unsupported by the Iceberg connector. The grant can be preserved in the migration for compatibility, but it must not be represented as a working Iceberg operation on this version. Read-only login checks showed `CURRENT_ROLE()` is `NONE` for `user_a`, `user_b`, and `write_service_account`; `admin` has `db_admin, cluster_admin, user_admin, security_admin`; `root` has `root`. The global `activate_all_roles_on_login` setting is `false`. No production grant, account, catalog, database, or data was changed.

The test writer login resolved to `lakehouse_writer`. The test-only external catalog and its synthetic database/table were dropped; the dedicated Hive/RustFS/PostgreSQL containers, volumes, and generated test credentials were removed. The disposable StarRocks FE/BE and test FreeIPA were left running as before. See the DML verification addendum in [Unit 5 Build and Test](../construction/plans/unit-5-build-and-test-plan.md).
