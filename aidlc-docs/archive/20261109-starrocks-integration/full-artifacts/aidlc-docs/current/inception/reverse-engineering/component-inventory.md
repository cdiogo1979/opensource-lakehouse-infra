# Component Inventory

## Application Packages
- `infra/starrocks/ldap-access`: role bootstrap. The legacy role design is reusable.
- `infra/starrocks/sql-bootstrap`: legacy SQL runner.

## Infrastructure Packages
- `infra/starrocks/{fe,be,preflight,kerberos,conf}`: legacy images and config.
- `docker-compose.deferred.yml`: inventory.
- Core and Airflow Compose files, `scripts/lakehouse.sh`, and `scripts/reset-lakehouse.py`.

## Shared Packages
- `infra/keycloak/realm-contract.json` and `bootstrap-realm.py`: groups and clients.
- `infra/polaris/*`: catalogs, roles, grants.
- `infra/rustfs/*`: buckets and policies.
- `infra/keycloak/bootstrap-users.json`: users.

## Totals
- Legacy StarRocks source: about 1,560 lines across 10 scripts, plus 2 Dockerfiles and 2 XML configs.
- Active v2 references to StarRocks: the deferred inventory entry, `scripts/bootstrap-starrocks-sql.sh`, and leftover `write-service-account` text in `infra/starrocks/ldap-access`.
