# Unit 5 Code Generation Plan — StarRocks Native LDAP Roles

## User-directed design update

On 2026-10-28 the user replaced the Ranger approach with StarRocks native roles/grants mapped to FreeIPA LDAP groups. This plan supersedes the Ranger implementation tasks. Do not add Ranger services or UserSync.

The exact StarRocks 4.1.6 security-integration documentation warns that its virtual-user mode requires Ranger for external authorization. Code generation therefore uses explicitly registered StarRocks users bound to FreeIPA DNs, an LDAP Group Provider, native roles/grants, and external-group role mappings. Password validation and group membership remain in FreeIPA.

## Generated code

- [x] `infra/starrocks/ldap-access/bootstrap_roles.py`: explicit-environment grant generation; LDAPS provider configuration; LDAP user registrations; native roles, grants, and external group mappings; exact disposable FE Docker identity/port guard; private secret file checks; sanitized output.
- [x] Added internal output databases `default_lh`, `default_lhdev`, and `default_lhuat`; writer-only scoped MV creation/management grants; developer MV read across all three; analyst MV read for prod only. General DDL/security administration remains excluded.
- [x] Recorded approved dual-use identity: `write-service-account` keeps its Kerberos keytab for Airflow/Spark and receives a separate FreeIPA LDAP password for StarRocks SQL over TLS; JupyterHub interactive login remains denied.
- [x] `scripts/bootstrap-starrocks-ldap-roles.sh`: repository wrapper for the bootstrap utility.
- [x] Unit 5 functional/NFR/infrastructure design updated to native StarRocks RBAC and direct Spark/RustFS boundary.
- [x] Add the isolated StarRocks LDAP test FE Compose service and LDAP auth TLS configuration. Do not use the existing FE, KDC, HMS, RustFS, volumes, or credentials.
- [x] Add protected test-only MySQL client option files and FreeIPA group-reader credential to the designated test secret directories. No production credentials were reused.
- [x] Confirm disposable source database lists (`test_prod`, `test_dev`, `test_uat`) are pairwise disjoint before apply.
- [x] Provision and test a disposable LDAP password for the writer identity through protected runtime files. Secret values were not written to source, args, SQL output, docs, or logs.
- [x] Verify on StarRocks 4.1.6 that the writer creates and synchronously refreshes an internal asynchronous MV from an isolated external Iceberg table, and that the grants permit the operation without general database/table DDL.
- [ ] Review existing default FE grants separately before any future production use. This test bootstrap must remain test-only.

## Scope and safety

The utility defaults to validation-only. It requires explicit environment database lists. Applying SQL requires a container named `starrocks-ldap-test-fe` with the exact Compose project/service labels and loopback SQL port `19030`, plus protected test-only credentials. It refuses all other targets. It does not revoke unspecified grants or execute against `iceberg-poc-starrocks-fe`.

## Documentation

The current Unit 5 functional design, NFR design, and infrastructure design now describe LDAP authentication, group resolution, native roles/grants, role exclusivity, cache/revocation limits, and the separate RustFS policy boundary. Ranger records remain only as historical Build and Test evidence and are explicitly superseded.
