# Unit 5 Deployment Architecture — StarRocks LDAP RBAC

## Production query path

```text
SQL client ── LDAPS credentials ──> FreeIPA
     │
     └── SQL session ──> StarRocks FE
                           ├── LDAP Group Provider ── LDAPS ──> FreeIPA groups
                           ├── native group-to-role grants
                           └── authorized query ──> StarRocks BE service identity
                                                        ├──> Hive Metastore
                                                        └──> RustFS

Spark client ── user RustFS credentials/policy ──> RustFS (independent path)
```

The production topology adds no Ranger service, database, UserSync, or Ranger network. FreeIPA remains the source of password and group state. StarRocks stores explicit LDAP user registrations, roles, and grants.

`write-service-account` is the one approved direct-role exception. StarRocks 4.1.6's asynchronous refresh worker did not inherit its LDAP group-derived role, so the account receives `lakehouse_writer` directly with `DEFAULT ROLE ALL` in addition to the `lakehouse-writers` mapping. This was verified by creating and synchronously refreshing an internal MV from an isolated external Iceberg table. Group removal does not revoke the direct assignment. For retirement or urgent revocation, disable FreeIPA authentication, close existing StarRocks sessions, and revoke/reset the direct StarRocks role.

## Isolated verification topology

The bootstrap script requires a dedicated disposable FE container with exact name `starrocks-ldap-test-fe`, Compose project and service labels equal to `starrocks-ldap-test`, and loopback-only SQL port `127.0.0.1:19030`. It rejects the existing FE and any container that fails these identity checks. Test LDAP bind and FE admin secrets must be in separate owner-only test directories. The target must attach only to the isolated FreeIPA test network and a dedicated StarRocks test network.

Before enabling the test FE, create its Compose definition using the pinned StarRocks 4.1.6 base image, a uniquely named FE metadata volume, no production data/credential mounts, and health checks. Configure LDAP authentication TLS and test CA trust only inside that test FE. No test container publishes LDAP, StarRocks BE, RustFS, or HMS ports.

## Provisioning command

Dry-run role scope and target validation:

```sh
./scripts/bootstrap-starrocks-ldap-roles.sh \
  --prod-databases default_lh \
  --dev-databases default_lhdev \
  --uat-databases default_lhuat
```

Apply only after test FE and test secret files are prepared:

```sh
./scripts/bootstrap-starrocks-ldap-roles.sh --apply \
  --prod-databases default_lh \
  --dev-databases default_lhdev \
  --uat-databases default_lhuat
```

Current bundle configuration names are `default_lh` (prod), `default_lhdev` (dev), and `default_lhuat` (UAT). Confirm those namespaces exist in the isolated test catalog before apply. The three lists must be disjoint. The script does not print SQL or secret values, and stops if the test FE labels/port do not match.

Isolated test evidence is recorded in `construction/plans/unit-5-build-and-test-plan.md`. It includes successful read/write authorization against a disposable Hive Iceberg catalog and the service-account MV refresh exception. No production grants or catalog were changed.

## Identity, role, and grant configuration

The test must verify the LDAP reader can resolve only the three configured group names and full DN membership from FreeIPA. It registers only the synthetic StarRocks SQL users and maps:

- `lakehouse-developers` → `lakehouse_developer`
- `lakehouse-analysts` → `lakehouse_analyst`
- `lakehouse-writers` → `lakehouse_writer`

Developer receives SELECT for all three explicit Iceberg source database lists and INSERT for dev only. Analyst receives SELECT for prod only. Writer receives SELECT/INSERT for all three. In the internal `default_catalog`, the test bootstrap creates `default_lh`, `default_lhdev`, and `default_lhuat` for materialized-view outputs: developer receives MV SELECT across all three; analyst receives MV SELECT in prod only; writer receives CREATE MATERIALIZED VIEW and MV ALTER/REFRESH/DROP/SELECT only in those three databases. No role receives general database/table DDL, user, role, security, or catalog administration. The writer SQL client must use a separately provisioned FreeIPA LDAP password and TLS; the identity remains excluded from JupyterHub login.

## Change and rollback

Test bootstrap changes only the named provider, test LDAP user registrations, role definitions, and their grants on the disposable FE. It does not remove unrelated users/grants. If any input, identity, or grant readback differs, stop and preserve the test FE for inspection. Do not change default/production FE or roll back by overwriting its grants. For production, first snapshot/read back current `SHOW USERS`, `SHOW ROLES`, and `SHOW GRANTS` under a separate approved change, then design an explicit reviewed migration and rollback.
