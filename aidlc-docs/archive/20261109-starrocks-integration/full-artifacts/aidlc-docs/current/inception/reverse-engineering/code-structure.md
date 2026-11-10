# Code Structure (StarRocks-relevant)

## Build System
- **Images and runtime**: Docker Compose V2 builds local images; Python 3 runs host scripts.
- **Tests**: pytest contract tests live under `tests/`, with no `__init__` files, so test basenames must be unique.

## Key Classes/Modules
### Existing Files Inventory
| Path | Purpose | Reuse in v2 |
|---|---|---|
| `infra/starrocks/fe/Dockerfile`, `be/Dockerfile` | StarRocks 4.1.6 plus krb5 and cron | Rewrite (drop Kerberos) |
| `infra/starrocks/fe/entrypoint.sh` (147 lines), `be/entrypoint.sh` (57) | Kerberos ticket, Hadoop config, FE/BE start | Rewrite |
| `infra/starrocks/kerberos/*`, `conf/core-site.xml`, `conf/hive-site.xml` | Kerberos and Hive config | Retire |
| `infra/starrocks/preflight/*` | Paired FE/BE state check | Review; possibly retire |
| `infra/starrocks/ldap-access/bootstrap_roles.py` (315) | LDAP group provider, native roles, environment grants, MV databases | Reuse the role and grant design; replace FreeIPA LDAP |
| `infra/starrocks/sql-bootstrap/runner.py` (834) | SQL canary and bootstrap against `iceberg-poc-starrocks-fe`, Hive-type catalog | Retire, or reuse the safe-client patterns |
| `scripts/bootstrap-starrocks-sql.sh` | Runs the runner | Replace |
| `docker-compose.deferred.yml` | Inventory entry for StarRocks | Update status |
| `scripts/bootstrap-default-product.sh` | Product bootstrap | Add a StarRocks catalog and roles step |
| `scripts/lakehouse.sh` | start/status/stop/reset | Add StarRocks commands |
| `scripts/reset-lakehouse.py` | Reset inventory | Add StarRocks volumes and networks |

## Design Patterns
### Optional overlay service set
Airflow uses `docker-compose.airflow.yml` together with dedicated `lakehouse.sh` subcommands. StarRocks can follow the same pattern.

### Idempotent, refuse-on-conflict bootstraps
Realm, policy, and Polaris bootstraps create missing objects, accept equal ones, and refuse conflicts without printing secrets.

### Group-named roles across services
RustFS policies, Polaris principal roles, Airflow, Jenkins, and Hub mappings all key on the Keycloak group names.

## Critical Dependencies
### StarRocks Iceberg REST catalog
Needs `iceberg.catalog.type=rest`, a URI, a warehouse, OAuth2 security properties, and S3 settings or vended credentials. The exact property set and the behavior of the StarRocks version need confirming during design.

### StarRocks authentication
Options are native users, LDAP (FreeIPA is retired), or OAuth2/JWT security integrations with a group provider in newer releases. Each needs confirming against the chosen version.
