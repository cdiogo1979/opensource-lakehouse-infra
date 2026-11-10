# Unit 5 Functional Design Clarifications

## Superseding decision — 2026-10-28

The Ranger-oriented clarifications below are historical and superseded by the user's choice to use StarRocks native roles and FreeIPA LDAP groups without Ranger. Current behavior and constraints are in `functional-design/business-logic-model.md`, `business-rules.md`, and `infrastructure-design/`.

## Native RBAC clarification — current

| Item | Resolved direction / recommendation | Evidence or remaining gate |
|---|---|---|
| StarRocks catalog | `iceberg` | Confirmed in the project's current README and SQL bootstrap. |
| Environment database names | prod `default_lh`; dev `default_lhdev`; UAT `default_lhuat` | Read from the current Airflow bundle environment configs. Keep all names explicit in the bootstrap invocation; do not grant to all databases. |
| FreeIPA group mapping | `lakehouse-developers` → developer role; `lakehouse-analysts` → analyst role; `lakehouse-writers` → writer role | Current FreeIPA bootstrap assigns each sample identity to one role group. Verify group membership on the isolated test FreeIPA before applying SQL. |
| Write scope | `INSERT` on existing Iceberg tables; separately, narrowly scoped internal materialized-view management for the writer | No general table/database DDL or security grants. The external Iceberg read/write matrix and forced writer MV refresh from an external Iceberg source passed on isolated StarRocks 4.1.6. |
| Writer SQL login | Approved: `write-service-account` also logs in to StarRocks to create and manage materialized views. | Its Kerberos keytab is not an LDAP password. Provision a separate protected FreeIPA password for LDAP SQL authentication and use TLS for the MySQL-protocol client connection. Keep this service identity denied from JupyterHub interactive login. |
| Materialized-view output | Approved recommendation: internal `default_catalog` databases `default_lh`, `default_lhdev`, and `default_lhuat`, matching the prod/dev/UAT environment names. | The bootstrap creates these databases only on the disposable FE. Source databases with the same names are in external catalog `iceberg`. The writer's forced synchronous refresh from an isolated external Iceberg table passed; production rollout still requires legacy-grant review. |
| Runtime application | Applied only to the disposable FE | The FE/BE LDAP role matrix, external Hive Iceberg read/write matrix, MV create/refresh/read, cache removal, unknown/no-role denial, and DDL/security denials passed. No production FE was targeted. |

## Additional verified writer constraint

The StarRocks 4.1.6 asynchronous MV refresh worker did not inherit the writer's LDAP group-derived role. The approved implementation grants `lakehouse_writer` directly to `write-service-account` and sets it as a default role. This persists after group removal. FreeIPA account disable blocks new logins, but active sessions remain usable; full revocation also requires closing sessions and revoking/resetting the direct role.

The user has resolved the writer login and materialized-view destination decisions. The disposable bootstrap now maps the writer role to narrowly scoped MV management grants and grants developer/analyst read-only access by environment. Do not provision or display the LDAP password in this code-generation step; an operator must set it in FreeIPA and deliver it through an approved protected credential channel before SQL login testing. Runtime SQL remains restricted to the isolated FE.

| Decision | Current direction |
|---|---|
| Authentication | FreeIPA LDAP over LDAPS; register SQL users in StarRocks with their FreeIPA DNs because the selected StarRocks 4.1.6 path uses native RBAC. Passwords remain in FreeIPA. |
| Group resolution | StarRocks LDAP Group Provider reads the three approved FreeIPA groups using a read-only bind and DN membership matching. |
| Authorization | Native StarRocks roles/grants map developer, analyst, and writer groups to explicit database scopes. No Ranger or UserSync. |
| Role policy | Developer reads all configured environments and inserts in dev; analyst reads prod only; writer reads/inserts all. DDL/security privileges are not granted by default. |
| Directory conflicts | The three role groups must be mutually exclusive because StarRocks combines mapped roles; reject conflicting membership in FreeIPA provisioning. |
| Transport | LDAPS with CA validation and TLS on StarRocks SQL client connections because LDAP authentication uses the MySQL cleartext authentication plugin. |
| Storage boundary | StarRocks roles apply only to StarRocks SQL. Direct Spark-to-RustFS continues to use RustFS IAM policies and per-user credentials. |
| Verification | Use only a disposable StarRocks FE and test FreeIPA identities; never apply bootstrap to the default FE. Measure group cache/revocation behavior without claiming immediate revocation. |

## Historical Ranger-oriented working decisions — superseded

The user approved the Unit 5 Functional Design Plan and requested continuation. The following recommended defaults are carried into the functional design for review; exact-stack behaviors remain Build and Test gates.

| Topic | Working decision | Verification / limitation |
|---|---|---|
| Human identity source | FreeIPA is canonical. Use StarRocks LDAP Security Integration and LDAP-backed group lookup so human accounts are not independently created in StarRocks, if the 4.1.6 combination with Ranger passes. | Test authentication, allowed group membership, username consistency in Ranger, group removal, and no local-user fallback. StarRocks docs say Security Integration requires Ranger authorization. |
| SQL authorization boundary | Use the StarRocks Ranger integration for all SQL resources queried through StarRocks, including the external Hive catalog. | Verify the exact catalog/database/table resources and SQL actions for StarRocks 4.1.6. No Hive Ranger plugin is assumed, and direct Spark is outside Ranger. |
| Ranger identity lifecycle | Ranger UserSync uses read-only LDAP to synchronize only approved FreeIPA users/groups. | Measure first-sync and group-removal propagation. Confirm nested-group handling and stale/deleted user behavior. |
| Role policy scope | Developer reads all environments and receives only approved DML writes in development; analyst reads production only; writer gets only approved DML writes across all environments; authorized administrator retains administrative privileges. | Schema DDL, user/role administration, grants, and Ranger policy changes remain administrator-only by default. If ETL requires DDL, identify the exact operation and scope before implementation. |
| Policy administration | Role membership is changed in FreeIPA; SQL privileges are changed in Ranger Admin policies. | Export/backup and change-control procedures are later operational design items. No custom policy reconciler is assumed. |
| Ranger compatibility | Keep StarRocks 4.1.6 as the existing candidate. Pin the exact Apache Ranger release only after compatibility checks. | Current docs list Ranger 2.1.0+ as minimum for StarRocks but do not certify this exact 4.1.6 combination. Ranger latest stable release may be evaluated, not assumed compatible. |
| Ranger service definition | Register the StarRocks service definition manually for the POC; the Ranger Admin-side StarRocks autocomplete plugin is optional. | The FE enforcement integration remains required. Verify artifact source, version, checksums, configuration, service-definition resource/action model, and policy polling. |
| Transport and policy conditions | Do not use Kerberos authentication between the StarRocks integration and Ranger; do not use JavaScript-evaluated Ranger policy conditions. | These limitations are stated in StarRocks' Ranger integration documentation. Select supported protected transport/credentials during infrastructure design. |
| Audit | Start with local StarRocks/Ranger audit files on isolated persistent test storage. | Validate allow/deny events and rotation. Centralized/durable audit retention is not claimed without a separate design. |
| Test state | Isolated FreeIPA, Ranger metadata, and disposable StarRocks FE/BE state; synthetic table/object names only. | Do not connect this test integration to production FreeIPA, RustFS, StarRocks volumes, or production objects. |

## Open verification items (not design blockers)

1. Does StarRocks 4.1.6 Security Integration plus LDAP Group Provider authenticate FreeIPA users and expose the exact role groups to the Ranger plugin?
2. Does the 4.1.6 Ranger integration authorize the current Hive external catalog across SELECT and the DML operations required for the role matrix?
3. What are the exact Ranger StarRocks service-definition resource and access-action identifiers for catalog/database/table/view/materialized-view resources in this pinned version?
4. What happens during Ranger Admin outage, with cached policies, for a previously authorized principal and for an uncached resource? What is the effective group/policy revocation delay?
5. Which DML operations must `write-service-account` perform in StarRocks? Current design excludes schema/security DDL by default.

If any of these checks fail, stop before production adoption and return to architecture design. Do not substitute native grants that bypass the role matrix or rely on Ranger for direct Spark access.

## Sources consulted

- [StarRocks Ranger integration](https://docs.starrocks.io/docs/administration/user_privs/authorization/ranger_plugin/)
- [StarRocks authentication and authorization overview](https://docs.starrocks.io/docs/best_practices/authentication_authorization/)
- [StarRocks security integration](https://docs.starrocks.io/docs/administration/user_privs/authentication/security_integration)
- [Apache Ranger downloads](https://ranger.apache.org/download.html)
- [StarRocks LDAP authentication](https://docs.starrocks.io/docs/administration/user_privs/authentication/ldap_authentication/)
- [StarRocks group provider](https://docs.starrocks.io/docs/administration/user_privs/group_provider/)
- [StarRocks Iceberg catalog DML](https://docs.starrocks.io/docs/data_source/catalog/iceberg/)
