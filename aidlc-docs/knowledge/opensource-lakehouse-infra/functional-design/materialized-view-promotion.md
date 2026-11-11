# Functional Design — Materialized View Promotion

Current design of how StarRocks materialized views travel from a product's dev MV database to UAT and production. Related: [`airflow-workflows.md`](airflow-workflows.md) (where the deploy runs), [`starrocks-sql-access.md`](starrocks-sql-access.md) (MV databases, writer login).

## Responsibility
Developers build and test views by hand in the dev MV database; the product repository declares them; the platform deploys them in UAT (`<product>-uat` bundle) and production (`<product>-main` bundle) as the product's writer, so views reach production through reviewed branches like code.

## Definitions (`lakehouse_dags.spec`, also run by Jenkins)
- `materialized_views/<project>/<name>.sql`; the file name is the view name: lowercase letters, digits and single `_`, at most 60 characters (no `__`: the deployer reserves `<name>__lakehouse_new`). Names are unique across subprojects.
- One statement: `CREATE MATERIALIZED VIEW ${mv_database}.<file name> ...`; leading `--` lines and a trailing `;` are ignored; any other `;` is refused. Only `${catalog}`, `${namespace}` and `${mv_database}` may appear; at most 100 000 bytes.
- The workflow name `deploy_materialized_views` is reserved.

## Deploy (`lakehouse_dags.mv_deploy`, `factory._deploy_materialized_views`)
- **Where**: every workflow DAG of a bundle with view files runs `deploy_materialized_views` after `validate_environment` and before its tasks (its failure stops the tasks; `stop_cluster` still runs); `<bundle>-deploy_materialized_views` runs it on demand and revokes its broker run afterwards. One task covers all views.
- **Values**: the scheduler reads the environment's `catalog`, `namespace` and `mv_database`, and `writer_user.username`, from the product file (`LAKEHOUSE_DATA_PRODUCTS_DIR`).
- **Login**: re-registering the run with the broker (control token) returns a fresh writer access token, bundle-checked by the broker; the deploy logs in to StarRocks (`starrocks-fe:9030`, TLS, `/run/certs/starrocks-ca.crt`) as the writer with that token through a client handler for `authentication_openid_connect_client`. The token is never logged or given to product code. `STARROCKS_ENABLED=false` skips the deploy with a warning.
- **Marker**: each deployed view's comment starts with `lakehouse-mv sha256=<first 16 hex of SHA-256 of the rendered statement>`, followed by the file's own comment.
- **Plan** (existing views read from `information_schema.materialized_views` and `tables`):
  - no view with a file's name -> create;
  - managed view, same digest -> unchanged (no SQL);
  - managed view, other digest -> replace: drop any leftover `<name>__lakehouse_new`, create it with the new definition, `ALTER MATERIALIZED VIEW <name> SWAP WITH <name>__lakehouse_new` (atomic), drop the staging name (now the old view);
  - managed view without a file -> drop;
  - a view without the marker -> never changed; reported if a file has its name.
- **Errors**: a create or replace failing with "Unknown table" (5502) is skipped (a later run creates it); any other failure is reported, the other views continue, and the task fails at the end naming the failed views; a failed replace leaves the current view.
- **Log**: `Materialized views in <db>: created [...], replaced [...], dropped [...], unchanged [...], skipped (source table missing) [...], made by hand [...], failed [...]`.

## Testable properties
- Deploying twice converges: after one apply the managed views equal the files (by digest), hand-made views are untouched, and a second apply creates, replaces and drops nothing (Hypothesis, `tests/airflow/test_mv_promotion.py`).

## Verification (2026-11-11, UAT, sample repository)
First deploy created `mv_tpch_current` and `mv_tpch_day_nation_segment` (refresh SUCCESS); a repeat was unchanged; an interval change replaced by swap; removing a file dropped the view; a `tpch_medallion` run deployed as its first step; the restore produced the original digests. Query rewrite used the aggregate once fresh (traced with `TRACE LOGS MV`).

## Limits
- A changed view is rebuilt from scratch: until its first refresh it is empty for direct reads, and rewrite falls back to the base tables. User decision: no synchronous refresh before the swap.
- Query rewrite needs SPJG views (no subqueries), freshness, and rollable aggregates (`SUM` yes, `COUNT(DISTINCT)` no).
- StarRocks' trace may keep listing `<name>__lakehouse_new` as related to the base tables after a swap (stale label; the view resolves by ID).
- Dev has no deploy: developers create dev views by hand.
