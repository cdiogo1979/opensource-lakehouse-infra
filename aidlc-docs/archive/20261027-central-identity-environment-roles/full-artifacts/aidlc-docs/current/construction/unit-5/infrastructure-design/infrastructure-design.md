# Unit 5 Infrastructure Design — StarRocks Native LDAP Roles

## Direction change

On 2026-10-28 the user superseded the approved Ranger design: use StarRocks native roles and grants mapped to FreeIPA LDAP groups; do not deploy Ranger or UserSync. The earlier Ranger compatibility investigation is historical and is no longer a Unit 5 dependency.

## Runtime boundaries

- Existing StarRocks FE/BE, its current named volumes, production catalog data, RustFS, Hive Metastore, KDC, and FreeIPA state remain protected.
- Bootstrap and integration tests target only the disposable FE named `starrocks-ldap-test-fe`, with Compose project/service labels `starrocks-ldap-test` / `starrocks-ldap-test-fe` and SQL published only on `127.0.0.1:19030`.
- The FE uses an isolated test FreeIPA endpoint and test-specific CA trust. Do not mount the production keytab, production RustFS secret, default FE metadata, or production network into the test FE.
- The test identity directory currently retained in the workspace was originally created as an isolated Ranger test fixture. It remains test-only; no Ranger process is required or used by the new role bootstrap. Rename its artifacts only as a separate cleanup task after confirming resource ownership.

## StarRocks LDAP and role configuration

StarRocks 4.1.6 uses LDAP authentication on explicitly registered StarRocks users because the security-integration virtual-user path is documented as requiring Ranger for external authorization. Register each login with its FreeIPA DN; password validation remains in FreeIPA. Configure LDAP host, port, TLS trust, and user search/direct-bind settings in the isolated FE configuration before testing.

Create the StarRocks LDAP Group Provider with:

- LDAPS URL and validated FreeIPA CA.
- Dedicated read-only bind identity.
- Group search rooted at the FreeIPA group base DN.
- Filter limited to `lakehouse-developers`, `lakehouse-analysts`, and `lakehouse-writers`.
- `cn` as group identifier and `member` as membership attribute; omit `ldap_user_search_attr` so StarRocks matches full DNs stored in FreeIPA group members.
- Explicit cache refresh/stale settings; measure effective revocation behavior.

The bootstrap creates native LDAP user registrations, three least-privilege roles, table/view grants in explicitly supplied databases, and `GRANT ROLE ... TO EXTERNAL GROUP ...` mappings. Database lists must be disjoint across production, development, and UAT. The bootstrap refuses all-database grants and does not create schema/security privileges.

| Role | Explicit production DB list | Explicit development DB list | Explicit UAT DB list |
|---|---|---|---|
| developer | SELECT | SELECT, INSERT | SELECT |
| analyst | SELECT | none | none |
| writer | SELECT, INSERT | SELECT, INSERT | SELECT, INSERT |

## Build and release boundary

`scripts/bootstrap-starrocks-ldap-roles.sh` invokes `infra/starrocks/ldap-access/bootstrap_roles.py`. A dry run validates target identity, input lists, and scope without applying SQL or displaying generated SQL. `--apply` additionally requires test-only secret files and rechecks Docker labels/loopback port before connecting. The script does not target the existing `iceberg-poc-starrocks-fe` container and does not run `REVOKE` against unspecified grants.

Production deployment is a separate approved operation. Before production rollout, inventory current StarRocks identities and grants, provision the mutually exclusive FreeIPA groups, configure trusted LDAPS, reconcile all SQL users/DNs, and review legacy broad grants. The current test script must not be repointed to production.

## Known boundaries

- StarRocks roles only control queries through StarRocks. Direct Spark-to-RustFS access remains governed by RustFS IAM.
- The service identity used by StarRocks to read HMS/RustFS remains separate from SQL users.
- `write-service-account` is intentionally a dual-use exception: its FreeIPA LDAP login is a StarRocks SQL user for MV management, while its Kerberos keytab remains the Airflow/Spark identity. StarRocks 4.1.6's refresh worker did not use the LDAP group-derived role. A direct `lakehouse_writer` role grant with `DEFAULT ROLE ALL` was required and passed a forced refresh from an external Hive Iceberg table. That assignment persists after FreeIPA group removal; account disable blocks new authentication but not existing SQL sessions. Revoke/reset the direct role and close sessions when retiring the account.
- StarRocks accumulates roles for all matched external groups; mutually exclusive data groups are enforced by FreeIPA provisioning. There is no deny-overrides mechanism for conflicting groups in this design.
- LDAP group/cache changes may not revoke active sessions immediately. Record observed behavior; no SLA is assumed.
- Only INSERT is granted by default for external tables. UPDATE/DELETE and DDL require separate compatibility and workload review.

## Isolated verification result — 2026-10-28

All 15 external-catalog role checks passed against synthetic Iceberg tables in a disposable Hive Metastore/RustFS stack. The writer created an internal manual-refresh asynchronous materialized view from `iceberg_test.test_prod.auth_probe`, forced a synchronous refresh, and read the materialized row. The test catalog, MV, containers, generated credentials/configuration, and dedicated database/object volumes were removed. The disposable StarRocks LDAP FE/BE and isolated FreeIPA remain for verification; no production FE, HMS, RustFS, data, or credentials were used.

## References

- [StarRocks LDAP authentication](https://docs.starrocks.io/docs/administration/user_privs/authentication/ldap_authentication/)
- [StarRocks LDAP Group Provider](https://docs.starrocks.io/docs/administration/user_privs/group_provider/)
- [StarRocks roles and privileges](https://docs.starrocks.io/docs/administration/user_privs/authorization/User_privilege/)
- [StarRocks security integration](https://docs.starrocks.io/docs/administration/user_privs/authentication/security_integration)
