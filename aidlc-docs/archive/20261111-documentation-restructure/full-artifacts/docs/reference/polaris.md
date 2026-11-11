# Polaris

Reference: the Iceberg catalog and its permissions. Back to the [README](../../README.md).

- **Catalogs**: three shared catalogs, one per environment. Each allows every product's bucket, and each product's namespace lives in its own bucket (this needs the Polaris feature `ALLOW_NAMESPACE_CUSTOM_LOCATION`, set in `infra/polaris/oidc.properties`).
- **Roles**: Polaris accepts Keycloak tokens and maps any product group (`role-<token>-<role>`) to the principal role of the same name.
- **Grants**: per product role and catalog, a catalog role with `NAMESPACE_LIST` and `CATALOG_READ_PROPERTIES`, plus the [level's privileges](../components.md#access-levels) on the product's namespace only. Grants that no product file describes are revoked and reported.
- **Principals**: Polaris needs a principal for every Keycloak user. The scheduled reconciler (`polaris-group-reconciler`, every `POLARIS_GROUP_RECONCILE_INTERVAL_SECONDS`, default 300) creates them and keeps their roles in sync with Keycloak groups. It runs the repository's current code (mounted read-only) and shows as `reconciler` in `./scripts/lakehouse.sh status`.
- **Storage credentials**: for each table it serves, Polaris issues short-lived RustFS credentials scoped to the table (one hour, cached for 10 minutes); workloads never receive root keys.
- **Management endpoint**: it stays inside the container (port 8182 is not published). Check readiness with `docker compose -f compose.core.yml exec polaris curl --fail --silent http://127.0.0.1:8182/q/health/ready`.
