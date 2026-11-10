# Unit 5 Functional Design — Business Rules

| ID | Rule |
|---|---|
| SR1 | FreeIPA owns user passwords and membership in `lakehouse-developers`, `lakehouse-analysts`, and `lakehouse-writers`. |
| SR2 | StarRocks 4.1.6 uses explicit native user registrations bound to FreeIPA LDAP DNs with the LDAP Group Provider. Security-integration virtual users are outside this native-RBAC design. |
| SR3 | Each canonical FreeIPA group maps to exactly one StarRocks role: developer, analyst, or writer. Role groups are mutually exclusive; conflicting memberships must be rejected by identity provisioning. |
| SR4 | Developer: SELECT in explicitly listed production, development, and UAT databases; INSERT only in explicitly listed development databases. |
| SR5 | Analyst: SELECT only in explicitly listed production databases. No development/UAT access or write grants. |
| SR6 | Writer: SELECT and INSERT in explicitly listed production, development, and UAT Iceberg databases. `write-service-account` logs in to StarRocks through FreeIPA LDAP and creates/manages materialized views in internal `default_catalog` databases `default_lh`, `default_lhdev`, and `default_lhuat`. Because the StarRocks 4.1.6 refresh worker does not inherit the LDAP group role, this account also receives a direct `lakehouse_writer` role grant with `DEFAULT ROLE ALL`; that grant persists after FreeIPA group removal. |
| SR7 | Unknown or unregistered users, and registered users without a recognized role group, receive no data permissions. No broad default role is granted. |
| SR8 | Bootstrap accepts disjoint database lists per environment and grants only against the configured external catalog. It does not infer location from database names or grant on all databases. |
| SR9 | Bootstrap is restricted to a dedicated disposable StarRocks FE and must refuse the default FE or any container without the exact isolated Compose identity. |
| SR10 | Existing catalog/user grants are inventoried before production application. Bootstrap does not silently revoke unrelated privileges; any broad grant that defeats the role matrix must be reviewed and explicitly removed separately. |
| SR11 | LDAP group lookup uses LDAPS with certificate validation and a read-only service identity. The FreeIPA built-in administrator is not used. |
| SR12 | Group changes apply to newly authenticated/resolved sessions according to observed StarRocks cache behavior. No immediate revocation SLA is assumed. |
| SR13 | StarRocks roles govern SQL through StarRocks only. Direct Spark-to-RustFS permissions continue to be enforced by RustFS IAM policies. |
| SR14 | StarRocks backend HMS/RustFS credentials are not exposed to SQL users and do not substitute for native StarRocks authorization. |
| SR15 | General privileges remain least-privilege. The writer role receives only the materialized-view-specific CREATE MATERIALIZED VIEW database privilege and ALTER/REFRESH/DROP/SELECT materialized-view privileges in the three approved output databases. `write-service-account` receives this role both from its FreeIPA group and a direct user grant required by refresh workers. It does not receive table/database mutation, GRANT, user/role administration, or catalog administration. |
| SR16 | Developer may SELECT materialized views in all three internal environment databases. Analyst may SELECT only production materialized views. Neither role may create, alter, refresh, or drop materialized views. |
| SR17 | `write-service-account` keeps its Kerberos keytab for Airflow/Spark and has a separate protected FreeIPA LDAP password for StarRocks SQL authentication. TLS is mandatory for its SQL client connection; the identity remains blocked from JupyterHub interactive login. Full revocation requires blocking new FreeIPA authentication, closing existing StarRocks sessions, and revoking/resetting the direct StarRocks role assignment. |

## Required Build and Test decisions

1. Verify the isolated FE's LDAP login config, FreeIPA CA trust, group filter, `member` membership attribute, username/DN matching, and read-only bind.
2. Read back StarRocks group-provider state, LDAP users, role definitions, role grants, and external-group mappings.
3. Test the allow/deny matrix for each supplied test database, including INSERT denial for developer prod/UAT, analyst dev/UAT, and unknown/unmapped principals.
4. Remove a test group membership and measure fresh-login, active-session, and LDAP group-cache behavior. Do not describe a measured cache delay as immediate revocation.
5. Verify all test operations target only the disposable FE and preserve existing FE/container/volume state.
6. Use Unit 3's separately completed direct Spark/RustFS matrix as evidence; StarRocks roles do not protect that path and must not be used as a substitute for RustFS IAM.
