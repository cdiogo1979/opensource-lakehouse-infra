# Functional Design — Identity, Lakehouse Access, and Workload Boundaries

## Environment data layout

Hive Metastore is the Iceberg catalog. RustFS stores the environment data in `lake` (production), `lake-dev` (development), and `lake-uat` (UAT). StarRocks reads external Iceberg data through the Hive catalog and RustFS. The separate `opensource-lakehouse` repository supplies Airflow DAG bundles and Spark workloads.

## Identity and access rules

The approved target identity groups and permissions are:

| Identity | RustFS / Spark access | StarRocks access target |
| --- | --- | --- |
| `developer-user` | Read all environments; write only `lake-dev` | Read all environment-scoped databases; write only development MV database |
| `analyst-user` | Read production only; no writes | Read production MV database only |
| `write-service-account` | Read/write all three environments | Read/write all environments and create/manage scoped materialized views |
| `admin` | Preserve existing administrator mapping | Preserve existing administrator privileges |

RustFS object policies enforce direct Spark access; Hive metadata visibility alone does not grant object access. StarRocks native roles map to FreeIPA LDAP groups. Because StarRocks MV refresh does not inherit LDAP group-derived roles in the tested topology, `write-service-account` has an approved direct writer-role exception. Offboarding must revoke that role and terminate active SQL sessions as well as remove LDAP membership.

StarRocks materialized views are scoped to `default_catalog.default_lh`, `default_catalog.default_lhdev`, and `default_catalog.default_lhuat`. The LDAP identity spelling `write-service-account` and existing StarRocks account `write_service_account` have not been proven to be the same principal; migration must resolve this before grants are transferred.

## Workload identity boundaries

Spark notebooks use the authenticated per-user identity and scoped object-store credentials in the approved design. Airflow initiates workload jobs using `write-service-account`; Airflow itself does not impersonate arbitrary users. Kerberos, Hive authorization, StarRocks SQL roles, JupyterHub login, and RustFS policies are independent controls. Authorization in one layer does not imply authorization in another.

## Verification status and limits

The role matrix and direct Spark/RustFS authorization passed in the documented unit tests, and StarRocks LDAP/native-RBAC behavior passed on disposable services. The overall AI-DLC intent closed with a user-approved verification waiver. Production account binding, provider setup, role/grant migration, identity migration, RustFS production-policy updates, MIT KDC cutover, and production authorization probes remain incomplete. Unit 2 FreeIPA membership variants, Unit 3 Hive metadata DDL/cache and Airflow integration, and Unit 4 user-facing denied-spawn behavior also retain the documented limits. These results do not establish production readiness.
