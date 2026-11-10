# Service Contracts — Central Identity and Environment Access

## FreeIPA

- Owns users, role groups, service principals, LDAP authentication, and Kerberos tickets.
- Planned role groups: `lakehouse-developers`, `lakehouse-analysts`, and `lakehouse-writers`; platform `admin` remains separate.
- Account and group administration is performed in FreeIPA. RustFS policy scope is not edited by changing group membership.
- TLS is required for LDAP client connections. Directory credentials and Kerberos keytabs remain protected secrets.

## Role policy document and reconciler

- A declarative, version-controlled document maps role groups to allowed bucket, prefix, and S3 actions.
- Policy document changes require Git review and are applied by the identity provisioner.
- FreeIPA group membership changes are reconciled into RustFS group membership and policy attachment.
- Reconciliation is idempotent, verifies exact effective policy, fails closed on unknown roles or unexpected broader permissions, and reports incomplete state.
- Reconciliation must preserve existing `lake` objects, `admin` privilege mapping, and the writer's RustFS S3 key. FreeIPA cutover reissues the writer's Kerberos keytab.

## RustFS

| Role | `lake` production | `lake-dev` development | `lake-uat` UAT |
|---|---|---|---|
| `lakehouse-developers` | Read | Read/write | Read |
| `lakehouse-analysts` | Read | Deny | Deny |
| `lakehouse-writers` / ETL service | Read/write | Read/write | Read/write |
| `admin` | Platform administrator | Platform administrator | Platform administrator |

RustFS checks S3 requests. Bucket listing is constrained to authorized prefixes; object actions are scoped to approved bucket/prefix resources. Analyst writes and developer writes outside development must be denied at RustFS.

## Hive Metastore and Spark

- Human Spark clients authenticate to HMS with their own Kerberos principal.
- HMS storage-based authorization remains the proposed metadata boundary, but the actual authorization behavior against S3A/RustFS must pass denied and allowed tests before the design can be considered verified.
- Spark uses a per-user RustFS IAM identity for human notebook access. The writer service identity remains for Airflow ETL only.
- If metastore authorization cannot reliably enforce user/database checks over S3A, pause cutover and revisit the authorization architecture; StarRocks SQL grants and UI filtering do not substitute for this direct access boundary.
- Database locations are explicit: `s3a://lake/warehouse/`, `s3a://lake-dev/warehouse/`, and `s3a://lake-uat/warehouse/`.

## JupyterHub

- Authenticates through FreeIPA LDAP over TLS and limits spawning to approved human users/groups.
- Notebook containers are isolated per user. Each receives only that user’s ticket cache/keytab and RustFS credential material.
- Removing a user’s role triggers RustFS policy reconciliation and termination of that user’s active notebook/Spark sessions; revoked credentials are deactivated where needed. No other user’s credentials may be mounted or readable.
- This design does not assume LDAP authentication itself issues a Kerberos ticket.

## StarRocks LDAP groups and native roles

- FreeIPA owns passwords and canonical role-group membership. StarRocks LDAP authentication validates users; the LDAP Group Provider resolves the three approved groups.
- StarRocks native roles and grants map `lakehouse-developers`, `lakehouse-analysts`, and `lakehouse-writers` to explicit Iceberg source and internal materialized-view database scopes.
- On StarRocks 4.1.6, this design uses explicitly registered LDAP users bound to their FreeIPA DNs. Security-integration virtual users are not part of the native-RBAC path.
- `write-service-account` is an approved LDAP SQL login for materialized-view work. It needs a separate protected FreeIPA LDAP password alongside its Kerberos keytab, and SQL clients must use TLS. It remains blocked from JupyterHub interactive login.
- Materialized views are stored in internal `default_catalog.default_lh`, `default_catalog.default_lhdev`, and `default_catalog.default_lhuat`. Developer can read all three, analyst only production, and writer can create/manage views in all three. General database/table/security administration remains denied.
- StarRocks FE/BE uses a separate service identity for HMS/RustFS. Native SQL roles do not authorize direct Spark/RustFS requests.
- Use LDAPS and TLS for SQL client connections. LDAP-authenticated MySQL clients use the cleartext authentication plugin; do not send passwords over an unencrypted SQL connection.
- Verify group mapping, SQL grants, cache/revocation behavior, and unknown-user denials against a disposable StarRocks FE before production rollout.

## Existing services and compatibility

- FreeIPA replaces the MIT KDC only after realm, principal, keytab, DNS, and service-ticket compatibility is verified.
- Existing Airflow writer workloads continue using `write-service-account`; human notebook identities are not substituted into the ETL path. The same account's approved StarRocks SQL login is for scoped materialized-view management.
- No production object migration or volume reset is allowed as part of ordinary provisioning or rollback.
