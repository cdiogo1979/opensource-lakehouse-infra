# Application Design — Materialized View Promotion

## Probe results that shape the design
- **P1**: StarRocks 4.1.7 logs in a user `IDENTIFIED WITH authentication_jwt` (Keycloak JWKS, `principal_field` `preferred_username`, `required_issuer` `http://keycloak.localhost:8080/realms/lakehouse`) with the writer's Keycloak access token; the client must speak `authentication_openid_connect_client` (a 10-line handler for pymysql). A user has one authentication method.
- **P2**: both tpch definitions are accepted on the Iceberg catalog (the latest-load-day subquery included) and refresh; `COMMENT` is returned by `information_schema.tables`; there is no `CREATE OR REPLACE` and the comment can't be altered, but `ALTER MATERIALIZED VIEW a SWAP WITH b` is atomic.
- **Broker**: re-registering an active run returns a fresh writer access token (control credential, bundle check by the broker).

## Components
| Component | Change |
|---|---|
| `lakehouse_dags.spec` (+ `validate`, used by Jenkins) | Discover and check `materialized_views/<project>/<name>.sql`: name rules, one `CREATE MATERIALIZED VIEW ${mv_database}.<file name>` statement, only `${catalog}`, `${namespace}`, `${mv_database}`, no `;` inside |
| `lakehouse_dags.mv_deploy` (new, standard library + pymysql) | Render a definition for an environment; compute the plan (create, replace, drop, keep) from the files and the MV database; apply it over TLS as the writer with the JWT; skip an MV whose source table is missing |
| `lakehouse_dags.factory` | Workflow DAGs of a bundle with MV files get `deploy_materialized_views` after `validate_environment` and before the tasks; a standalone `<bundle>-deploy_materialized_views` DAG (register, deploy, revoke). The deploy task gets the writer token by re-registering the run with the broker |
| StarRocks users (`reconcile-starrocks-users.py`, bootstrap) | Product writer users `srv-<product>-writer` become `IDENTIFIED WITH authentication_jwt`; people keep LDAP |
| Compose (Airflow scheduler) | Mount the StarRocks CA read-only; the scheduler already shares the `core` network with the StarRocks FE |
| Product file | No change: the environment's `catalog`, `namespace` and `mv_database` fill the placeholders (read by the scheduler from the product index, as for checkpoint buckets) |
| Sample repository | `materialized_views/tpch/mv_tpch_current.sql`, `materialized_views/tpch/mv_tpch_day_nation_segment.sql`; tests; README; AGENTS.md; canonical knowledge |

## Rules
- **Managed MVs**: the deployer writes `COMMENT 'lakehouse-mv sha256=<hash of the rendered statement>; <the file's own comment>'`; only MVs whose comment starts with `lakehouse-mv` are replaced or dropped. Hand-made MVs are never touched; a hand-made MV with a file's name is reported and left alone.
- **Plan**: file without MV -> create; managed MV with a different hash -> replace (create `<name>__lakehouse_new`, `SWAP WITH`, drop the old one); managed MV without a file -> drop; same hash -> keep.
- **Missing source table**: the create fails with an unknown-table error -> reported as skipped; the task succeeds; a later run creates it.
- **Identity**: every statement runs as `srv-<product>-writer`; StarRocks' grants bound it (create only in the product's MV databases, read only its namespaces). The token comes from the broker and is never logged or given to product code.

## Decision for the user
Switching writer users to JWT means `srv-<product>-writer` can no longer log in to StarRocks with its password (for example from DBeaver). People are unaffected.
