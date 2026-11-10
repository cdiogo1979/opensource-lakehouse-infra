# Code Summary — rename

## Platform (this workspace)
| File | Change |
|---|---|
| `data-products/default.yaml` | `repo.url` → `https://github.com/cdiogo1979/opensource-lakehouse-sample-dp.git` |
| `README.md` | the product example, two clone URLs, two mentions of the repository |
| `tests/jenkins/test_product_pipelines.py` | the expected remote and `repository('opensource-lakehouse-sample-dp')` |
| `tests/products/test_repo_and_bundles.py` | the fixture compared with `default.yaml` (not in the plan: found by the suite) |

Kept on purpose: `tests/operations/test_reset_lakehouse.py` and `tests/airflow/test_bundle_root_contract.py` check that no sibling `../opensource-lakehouse` path is used.

## Workload repository (scratchpad clone, branch `repository-rename` from `42de0f3`; not pushed)
- Remote URL → `https://github.com/cdiogo1979/opensource-lakehouse-sample-dp.git`.
- Commit `932feee`: the three notebooks' Initialization line, README, AGENTS.md, `tests/workload_foundation/test_jupyter_scripts.py` use `~/work/opensource-lakehouse-sample-dp` and the new URL.

## Tests run
- Host suite 530 passed, 3 skipped.
- Workload repository 85 passed, 1 skipped (DuckDB); `scripts/code_quality.sh all` passed.
