# PR request — Materialized view promotion; writer token login; staged-mount fix

## Problem
Developers could build StarRocks materialized views only in dev; UAT and prod views had to be made by hand, and nothing automatic could log in to StarRocks.

## Solution
- **Declared views**: a product repository's `materialized_views/<project>/<name>.sql` (one `CREATE MATERIALIZED VIEW ${mv_database}.<name>` statement, `${catalog}`, `${namespace}`, `${mv_database}` placeholders), checked by `lakehouse-validate-workflows` in CI.
- **Deploy**: new `lakehouse_dags/mv_deploy.py`; every workflow DAG of a bundle with views runs `deploy_materialized_views` before its tasks, and `<bundle>-deploy_materialized_views` runs it on demand. As the product writer it creates new views, replaces changed ones (create, `SWAP WITH`, drop), drops managed views whose file is gone, leaves unchanged and hand-made views alone, and skips views whose source table is missing. Managed views carry `lakehouse-mv sha256=<digest>` in their comment.
- **Writer token login**: the reconciler keeps product writers on `authentication_jwt` (Keycloak keys and issuer, `preferred_username`) and people on LDAP; the deploy gets the writer token from the broker (re-registering the run) and logs in over TLS with a small OpenID Connect client handler. No password in the deploy path.
- **Wiring**: scheduler mounts the product files, `data_products.py` and the StarRocks CA; `materialized_views` added to bundle `sparse_dirs`; `materialized_views` validator output.
- **Fix (CR-2)**: `prepare-runtime.py`, `prepare-starrocks-certificates.py` and `prepare-ldap-certificates.py` keep an unchanged staged mount (and its inode); before, every start replaced them and containers that weren't recreated (the core reconciler after `start-airflow`) failed every cycle.
- Docs: data products (promotion, rewrite), StarRocks, security, limitations, developer journey.

## Verification
Host 628 passed, 3 skipped; Airflow image 118 passed; StarRocks 49 passed. Live UAT: first deploy, unchanged repeat, replace by swap, drop on removal, deploy as the first pipeline step, restore; query rewrite to the aggregate traced.

## Deployment
Applied: reconciler restarted (writer switched to token login), `start-airflow`. Sample repository `main` and `uat` at `925ef51`.

## Risks and limitations
Writers can no longer log in to StarRocks with a password. A changed view is rebuilt (its first refresh runs again). Views with subqueries are read by name only (no query rewrite).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
