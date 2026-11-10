# Unit 5 Functional Design — StarRocks Native LDAP Authorization

## Purpose

Use FreeIPA as the source of login credentials and role-group membership for StarRocks SQL. StarRocks' LDAP group provider resolves FreeIPA groups, and StarRocks native roles and grants enforce SQL access. Apache Ranger is removed from the target design.

This design concerns queries issued through StarRocks. Spark clients that read or write RustFS directly remain governed by their own RustFS IAM credentials and policies. StarRocks uses its backend service identity to access HMS and RustFS after StarRocks authorizes the SQL session; native StarRocks roles do not change that storage identity.

## Actors and trust boundaries

1. **FreeIPA** owns human and service account passwords and canonical membership in `lakehouse-developers`, `lakehouse-analysts`, and `lakehouse-writers`.
2. **StarRocks LDAP authentication** validates a login against FreeIPA. With StarRocks 4.1.6, use explicitly registered StarRocks users bound to their LDAP DNs; do not use the security-integration virtual-user mode for this native authorization design.
3. **StarRocks LDAP group provider** performs protected LDAP group lookups and returns matching FreeIPA group names to the authenticated SQL session.
4. **StarRocks native RBAC** maps each external LDAP group to a StarRocks role and applies that role's catalog/database/table privileges.
5. **StarRocks FE/BE service identity** accesses Hive Metastore and RustFS for an authorized query. It is not the requesting user and does not replace the SQL authorization decision.
6. **RustFS** independently enforces S3 permissions for direct Spark requests and StarRocks backend requests.

## Authorization flow

```text
FreeIPA username/password ── LDAP authentication ──> registered StarRocks SQL user
FreeIPA group membership ── LDAP Group Provider ──> external group in SQL session
                                                          │
                                                          v
                                    external group → native StarRocks role
                                                          │ catalog/database/table grants
                                                          v
                                      StarRocks authorization decision
                                                │ allow only
                                                v
                             StarRocks service identity → HMS / RustFS

Direct Spark user → RustFS using that user's S3 credentials (separate path)
```

## Role-to-resource policy

The bootstrap accepts explicit, disjoint lists of Hive database names for each environment. It never infers an environment from an arbitrary database name or broadens a grant to all databases.

| FreeIPA group | Production data / views | Development data / views | UAT data / views | DDL and security administration |
|---|---|---|---|---|
| `lakehouse-developers` | SELECT on Iceberg data and internal MVs | SELECT, INSERT on Iceberg data; SELECT on internal MVs | SELECT on Iceberg data and internal MVs | Denied |
| `lakehouse-analysts` | SELECT on Iceberg data and internal MVs | Denied | Denied | Denied |
| `lakehouse-writers` | SELECT, INSERT on Iceberg data; create/manage internal MVs | SELECT, INSERT on Iceberg data; create/manage internal MVs | SELECT, INSERT on Iceberg data; create/manage internal MVs | General DDL/security denied |
| Unknown/unmapped | Denied | Denied | Denied | Denied |

The external catalog's database names must be supplied explicitly and must not overlap between environments. Internal materialized-view destinations are `default_catalog.default_lh`, `default_catalog.default_lhdev`, and `default_catalog.default_lhuat`; output and source names may match because they are in different catalogs. `write-service-account` uses its FreeIPA LDAP password over TLS to StarRocks SQL and has narrow MV creation/management rights. Its Kerberos keytab remains for Airflow/Spark. StarRocks 4.1.6's MV refresh worker does not inherit the FreeIPA group-derived writer role, so the approved exception grants `lakehouse_writer` directly to `write-service-account` and sets it as a default role. This direct assignment remains after FreeIPA group removal; disable the directory account to block new logins, close active StarRocks sessions for immediate revocation, and revoke the direct role/reset its default role when retiring the account. StarRocks grants authorize SQL operations; RustFS policies remain the enforcement boundary for direct Spark object access. INSERT is the only write privilege granted by default for external Hive/Iceberg tables. UPDATE/DELETE, general database/table schema changes, and security administration remain denied.

## Identity and role lifecycle

- FreeIPA is authoritative for passwords and group membership. StarRocks stores a login registration and LDAP DN for each SQL principal because the selected native-RBAC path uses manually registered LDAP users.
- The FreeIPA groups are the role mapping source. Bootstrap grants each StarRocks role to its corresponding external group.
- The three role groups must be mutually exclusive. StarRocks applies all roles resolved from group membership; it does not provide a deny-overrides rule for conflicting memberships. Conflicting assignments must be rejected in FreeIPA provisioning and covered by a membership audit.
- The StarRocks LDAP group-reader account is read-only and may read only the users/groups required for authentication and mapping. It is not the FreeIPA administrator.
- An unknown user has no StarRocks registration. A registered user with no recognized group receives no data role.
- Existing native privileges on the target catalog must be inventoried before application. This bootstrap does not revoke or alter unrelated grants. Do not apply it to a production FE until its existing grants have been reviewed.
- Administrator access remains a separate, protected StarRocks administrator mapping and is not inferred from these data groups.

## Safe error behavior

- LDAP authentication failure, invalid TLS, unknown user, or directory outage denies login; the configured StarRocks group-provider cache may preserve an existing mapped role for its bounded stale window.
- Group lookup failure must not grant an additional role. The observed cache behavior and session lifetime must be measured; this design makes no immediate-revocation promise.
- A registered user without a mapped group, or a query outside its role grants, is denied by StarRocks native authorization.
- Hive Metastore/RustFS backend failures fail the query; StarRocks does not retry under the requesting user's credentials or another service account.
- Logs may identify principal, role, resource, action, and result, but must not include passwords, bind credentials, S3 keys, keytabs, ticket contents, or sensitive query literals.

## Verification boundary

Build and Test must use a disposable StarRocks 4.1.6 FE and isolated FreeIPA identities. Verify LDAP login, group lookup, role readback, production/dev/UAT SELECT and INSERT allow/deny behavior, MV create/manage/read boundaries, denial of unrelated DDL, unknown identities, absent group membership, role removal, cache refresh, active-session behavior, and that no mutation reaches the default StarRocks FE or production data. A successful StarRocks denial does not prove RustFS direct access is denied; direct Spark/RustFS tests remain separate.

## Official StarRocks documentation

- [LDAP authentication](https://docs.starrocks.io/docs/administration/user_privs/authentication/ldap_authentication/) — manual LDAP users, explicit DNs, and group-provider DN matching.
- [LDAP group provider](https://docs.starrocks.io/docs/administration/user_privs/group_provider/) — LDAP group lookup, cache behavior, and `GRANT ... TO EXTERNAL GROUP`.
- [Manage user privileges](https://docs.starrocks.io/docs/administration/user_privs/authorization/User_privilege/) — native roles and external catalog grants.
- [GRANT syntax](https://docs.starrocks.io/docs/sql-reference/sql-statements/account-management/GRANT/) and [privilege items](https://docs.starrocks.io/docs/administration/user_privs/authorization/privilege_item/) — database-level CREATE MATERIALIZED VIEW and materialized-view SELECT/ALTER/REFRESH/DROP privileges.
- [CREATE MATERIALIZED VIEW](https://docs.starrocks.io/docs/sql-reference/sql-statements/materialized_view/CREATE_MATERIALIZED_VIEW/) — external catalog source and manual refresh constraints. StarRocks 4.1.6 external Iceberg source creation and forced synchronous refresh passed on the disposable stack.
- [Security integration](https://docs.starrocks.io/docs/administration/user_privs/authentication/security_integration) — version-specific boundary; the 4.1 documentation warns that virtual-user security integration requires Ranger for external authorization, so this design uses manually registered LDAP users with native RBAC.
