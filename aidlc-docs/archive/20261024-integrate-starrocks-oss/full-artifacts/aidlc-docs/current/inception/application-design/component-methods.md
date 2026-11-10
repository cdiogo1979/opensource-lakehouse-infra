# Component Methods — StarRocks OSS Integration

These are high-level operation contracts, not implementation details. Script names, SQL syntax, exact arguments, error handling, and configuration schemas are assigned to Construction Functional Design.

## Identity Provisioning

| Operation | Inputs | Outputs | Purpose |
|---|---|---|---|
| `provision_starrocks_hms_identity(config) -> ProvisioningResult` | Realm/service identity settings, KDC access, protected credential directory | Dedicated service principal and keytab reference; redacted status | Create or reuse StarRocks-only Kerberos credentials for HMS access without rotating existing identities. |
| `provision_starrocks_rustfs_identity(config) -> ProvisioningResult` | RustFS administrative access, bucket and warehouse prefix, protected credential directory | Dedicated access/secret key references and scoped policy status | Create or reuse a StarRocks-only object-store identity with warehouse-prefix read/write permissions. |
| `render_starrocks_identity_contract(credential_refs) -> RuntimeConfig` | Keytab/config references and S3 credential references | Mounted runtime configuration with no literal secret values in tracked files | Make service credentials available to StarRocks using the approved mounted-file/environment contract. |

## StarRocks Runtime

| Operation | Inputs | Outputs | Purpose |
|---|---|---|---|
| `start_starrocks(compose_config) -> RuntimeStatus` | Compose project/configuration and required mounted credential references | FE/BE service status | Start the single FE/BE deployment and report service state. |
| `check_starrocks_readiness(endpoint) -> ReadinessResult` | Internal FE readiness endpoint and Compose service state | Ready/not-ready result with redacted diagnostics | Gate catalog/account bootstrap on FE availability and service health. |
| `connect_sql(endpoint, sql_identity) -> SqlSession` | Loopback or internal SQL endpoint and StarRocks SQL account | SQL session or redacted connection failure | Establish native SQL client access for users or the bootstrap operation. |

## StarRocks SQL Bootstrap

| Operation | Inputs | Outputs | Purpose |
|---|---|---|---|
| `configure_iceberg_catalog(sql_session, catalog_config) -> CatalogStatus` | StarRocks SQL session and HMS/RustFS catalog parameters plus secret references | Catalog create/reconcile status | Register or reconcile the external Iceberg catalog that uses the existing HMS and RustFS. |
| `provision_sql_accounts(sql_session, account_config) -> AccountStatus` | Admin bootstrap session and generated account credential references | Redacted account reconciliation status | Create/reconcile native SQL users and role membership without exposing generated passwords. |
| `apply_access_matrix(sql_session, grants_config) -> GrantStatus` | Admin bootstrap session, catalog/database names, and approved role matrix | Redacted grant reconciliation status | Apply least-privilege read/write/admin grants aligned with the approved matrix. |
| `run_bootstrap(config) -> BootstrapResult` | Runtime readiness, protected credential references, catalog settings, and account/grant definitions | Repeatable success/failure summary with redacted diagnostics | Orchestrate catalog and account setup through an explicit operator-invoked command. |

## Existing Shared Lakehouse Services

| Operation | Provider | Purpose |
|---|---|---|
| `get_iceberg_metadata(catalog, namespace, table)` | Hive Metastore via StarRocks Iceberg catalog | Resolve Iceberg table metadata while authenticating as the StarRocks service identity. |
| `read_or_write_iceberg_data(table, operation)` | RustFS through StarRocks Iceberg connector | Read data or commit supported writes using StarRocks' dedicated S3 identity. |
| `issue_service_ticket(principal, keytab)` | Kerberos KDC / StarRocks runtime login | Obtain and refresh the service TGT for secured HMS access; lifecycle specifics remain for NFR/Infrastructure Design. |

## SQL Clients and Operations

| Operation | Inputs | Outputs | Purpose |
|---|---|---|---|
| `execute_sql(endpoint, credentials, statement) -> QueryResult` | Loopback SQL endpoint, StarRocks native account, SQL statement | Result set or authorization/SQL error | Provide user query and controlled write access governed by native StarRocks privileges. |
| `run_operator_bootstrap(command, config_refs) -> BootstrapResult` | Documented command, service readiness, and protected config references | Redacted bootstrap status | Let an operator repeatably initialize/reconcile the catalog and SQL access after startup. |
