# StarRocks LDAP group roles

`bootstrap_roles.py` creates the FreeIPA LDAP group provider, StarRocks LDAP user registrations, native roles/grants, and external-group mappings for an isolated FE. The shell entry point is `scripts/bootstrap-starrocks-ldap-roles.sh`.

## Access model

- `lakehouse-developers` → `lakehouse_developer`: SELECT from the supplied prod/dev/UAT databases; INSERT in dev only.
- `lakehouse-analysts` → `lakehouse_analyst`: SELECT from the supplied prod database list only.
- `lakehouse-writers` → `lakehouse_writer`: SELECT and INSERT across all supplied environment lists.
- The bootstrap also creates environment-scoped databases in StarRocks' internal `default_catalog`: `default_lh`, `default_lhdev`, and `default_lhuat` by default. Developer gets SELECT on materialized views in all three; analyst gets SELECT on production materialized views only; writer gets SELECT and the scoped CREATE/ALTER/REFRESH/DROP privileges on materialized views in all three.

Groups must be mutually exclusive because StarRocks combines grants from every matched group. FreeIPA owns passwords and group membership. StarRocks stores a native user registration for each LDAP login and constructs the user's DN from the FE direct-bind pattern; do not register an explicit per-user DN because that legacy form does not support LDAP group resolution. Unknown/unmapped principals receive no data role. General schema and security privileges are not granted; the writer role receives only CREATE MATERIALIZED VIEW at database scope and ALTER/REFRESH/DROP on materialized views in the three approved output databases. The FE entrypoint persists `group_provider = lakehouse_freeipa_groups` in `fe.conf`, and the bootstrap applies the dynamic setting after creating the provider, so native LDAP logins resolve these mappings across FE restarts.

`write-service-account` is both the Airflow/Spark workload identity and an approved StarRocks SQL login for materialized-view management. Its Kerberos keytab is not an LDAP password. An administrator must provision a distinct FreeIPA LDAP password for this account, protect it as a client credential, and require TLS on StarRocks MySQL-protocol connections before enabling SQL login. Keep JupyterHub interactive-login policy unchanged: this service identity is not a notebook user.

## Bootstrap safety boundary

The utility refuses to apply unless Docker metadata identifies the container `starrocks-ldap-test-fe`, Compose project/service `starrocks-ldap-test` / `starrocks-ldap-test-fe`, and confirms that no host port is published. SQL runs only through `docker exec` inside this disposable FE. It requires the LDAP bind credential below `.runtime/ranger-test/secrets/` and the MySQL option file below `.runtime/starrocks-ldap-test/secrets/`, both mode 0600. This test guard intentionally prevents applying the script to the existing `iceberg-poc-starrocks-fe`.

The disposable FE/BE Compose topology, protected test secrets, and isolated synthetic databases are present. The bootstrap has been applied successfully to that FE, and readback confirms the provider, roles, grants, external-group mappings, and internal materialized-view databases. The FE must also set the cluster-wide `group_provider` parameter to `lakehouse_freeipa_groups`; otherwise native LDAP users authenticate successfully but resolve `CURRENT_GROUP()` as `NONE`. The bootstrap sets this parameter. Do not point the script at a live FE.

Supply actual database names from the disposable catalog, separated by commas and with no overlap:

```sh
./scripts/bootstrap-starrocks-ldap-roles.sh \
  --catalog default_catalog \
  --prod-databases test_prod \
  --dev-databases test_dev \
  --uat-databases test_uat
```

This is validation-only. Add `--apply` after the test FE and test-only files are in place. The script does not print generated SQL, LDAP credentials, or MySQL error details. On the disposable StarRocks 4.1.6 FE, each apply drops and recreates only the named test group provider, then reasserts the declared roles/grants and external-group mappings. It does not revoke unrelated privileges. This behavior is deliberately confined to the guarded test FE.

For this runtime test, the source test databases are synthetic tables in `default_catalog`; the command sets `--catalog default_catalog`. In the target deployment, pass the actual external Hive catalog name (expected to be `iceberg`) and its environment database names. The three `--mv-*-database` options default to `default_lh`, `default_lhdev`, and `default_lhuat`, created only in the internal `default_catalog` and kept separate from the external source catalog. Change the names only when the approved environment mapping changes. Runtime acceptance must verify exact 4.1.6 materialized-view grants and query behavior before any production rollout.

## TLS requirements

Use LDAPS with CA validation for user authentication and group lookup. StarRocks LDAP authentication clients send the LDAP password using the MySQL cleartext authentication plugin, so client connections to the StarRocks SQL protocol must also use TLS; do not expose an LDAP-authenticated SQL port without it. Configure and test this before production login enablement.

## StarRocks 4.1.6 constraint

The 4.1 documentation warns that security-integration virtual users require Ranger for external authorization. This implementation instead uses registered LDAP users with native StarRocks RBAC and an LDAP Group Provider. Confirm the exact 4.1.6 behavior on the disposable FE before any production migration.

## Isolated runtime test status — 2026-10-28

- The test FE and BE are healthy on the internal `ranger-test-ipa-net`, with no host ports published. Their state is in the named `starrocks-ldap-test-*` volumes.
- TLS admin login to the disposable FE succeeded. FreeIPA's group provider is configured with LDAPS and CA validation; `SHOW CREATE GROUP PROVIDER` masks its bind password.
- The bootstrap applied three native roles, environment-scoped grants, internal output databases, and `GRANT ... TO EXTERNAL GROUP` statements. Root readback confirms role scopes and output databases.
- Direct OpenLDAP bind and all three StarRocks LDAP logins succeed over CA-verified LDAPS. The JNDI failures came from newline-terminated input files passed unchanged to `ldappasswd -T`, while StarRocks credentials were read without the final newline. The test FreeIPA bootstrap now normalizes password-file bytes before setting passwords.
- Native LDAP logins resolve the expected FreeIPA group and StarRocks role after the bootstrap sets `group_provider` to `lakehouse_freeipa_groups`.
- The source-table allow/deny matrix passed: developer reads prod/dev/UAT and writes dev only; analyst reads prod only and cannot write; writer reads/writes all three. The MV read matrix passed: developer reads all output databases; analyst reads prod only; writer reads all. Writer create/alter/drop passed in all three output databases; analyst/developer refresh was denied.
- StarRocks' asynchronous MV refresh worker does not inherit the writer's LDAP group-derived role. The approved exception is a direct `lakehouse_writer` grant with `DEFAULT ROLE ALL` for `write-service-account`, in addition to its FreeIPA group mapping. Forced refresh passed in all three output databases. FreeIPA group removal alone will not revoke this account's StarRocks access; the isolated test confirmed that disabling the FreeIPA account blocks LDAP SQL login, and re-enabling it restores login.
- A registered LDAP account with no mapped role group authenticated with no current group or role and was denied source data. Disabling the writer account denied new login, while an existing SQL session remained active and query-capable; close existing StarRocks sessions as part of urgent revocation.
- External-group mappings have no separate `SHOW GRANTS` readback, but all three LDAP users logged in and their effective groups/roles and positive/negative source and MV access were verified.
- Production StarRocks, FreeIPA, object storage, and their data were not changed. Only isolated FE/BE and FreeIPA test services remain running; Ranger Admin, DB, and UserSync are not used by this native-RBAC design and remain removed.

The tested bootstrap still has a strict disposable-FE guard and must be adapted to production paths and service topology before live use. The writer direct-role exception is narrowly limited to `write-service-account`; developer and analyst access remains group-derived. This runtime test is against synthetic databases in `default_catalog`; verify real Hive external catalog behavior, TLS-enabled production login, and any existing external tables separately before production rollout.

### Writer account lifecycle

The direct StarRocks writer role is required for asynchronous MV refresh and is intentionally persistent across FreeIPA group changes. To block new logins, disable `write-service-account` in FreeIPA (`ipa user-disable write-service-account`) and verify LDAP authentication fails. Testing confirmed that an already-open StarRocks SQL session remains query-capable after account disable, so immediate full revocation also requires an operator to close that user's existing StarRocks sessions. For permanent retirement, an administrator must also revoke the StarRocks direct role and reset its default role. Re-enabling the FreeIPA account alone restores the direct StarRocks role's effective access; treat that as a privileged service-account lifecycle operation.
