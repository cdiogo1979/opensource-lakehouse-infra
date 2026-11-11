# Build and Test Summary — Materialized View Promotion

| Check | Result |
|---|---|
| Infra host pytest | 628 passed, 3 skipped (incl. MV rules, deploy plan property, writer token logins, staging inode test) |
| Airflow-image tests (`scripts/verify/dag-factory-tests.sh`) | 118 passed |
| StarRocks tests | 49 passed (P2b: every user ends on its login method) |
| Sample repository pytest / code quality | 110 passed, 2 skipped / PASS |
| `lakehouse-validate-workflows` on the sample repository | OK: 3 workflow(s), 2 materialized view(s) |
| Reconciler cycle (live) | Polaris principals=6; `srv-default-writer` switched to token login in place |
| Bundle checkout | `materialized_views` added to `sparse_dirs` (found live: the DAG was missing); `start-airflow` synced the checkouts |
| Live 1: first deploy (`live_mv_deploy_1`) | created both views in `default_lhuat` as the writer (token login); active, first refresh SUCCESS; 60175 and 14588 rows |
| Live 1b: repeat (`live_mv_deploy_2`) | unchanged both; no SQL |
| Live 2: definition change (`live_mv_change`) | `mv_tpch_current` replaced by swap (new hash, 30-minute interval, no staging left); the other unchanged |
| Live 3: file removed (`live_mv_remove`) | `mv_tpch_day_nation_segment` dropped; `mv_tpch_current` unchanged |
| Live 4: pipeline (`live_mv_pipeline`, `default-uat-tpch_medallion`) | success; deploy ran first in the pipeline (unchanged) |
| Live 5: restore (`live_mv_restore`) | aggregate re-created, `mv_tpch_current` replaced back; hashes equal the first deploy's |
| Query rewrite (user-reported, traced) | revenue query rewritten to `mv_tpch_day_nation_segment` once fresh; `mv_tpch_current` not rewritable (subquery: not SPJG); `COUNT(DISTINCT)` blocks rollup; trace shows a stale `__lakehouse_new` label after swaps (documented) |

Live 4 ran on the removal commit because a `git revert -q` failed and the wait loop saw the bundle already current; the revert was redone and deployed in Live 5.
