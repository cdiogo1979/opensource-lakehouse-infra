# Code summary: data product Airflow bundles

Intent `20261109-data-product-airflow-bundles`, unit `airflow-bundles`. Traces to FR-1 to FR-5, BR-1 to BR-6, and CR-1 (no writer field in the YAML).

## Changed and new files
| Area | Files | What changed |
|---|---|---|
| Product model | `infra/products/data_products.py`, `infra/products/template.yaml`, `data-products/default.yaml` | Optional `repo` block (`url`, `prod_branch`, `uat_branch`) with https-only, credential-free URL and safe branch rules; `bundle_config`, `bundle_names`, `DAG_ID_PATTERN`, `product_for_dag_id`. `default` uses `opensource-lakehouse` (`main`/`uat`). |
| Bundle list | `scripts/setup/airflow-bundle-config.py`, `infra/airflow/validate-bundle-config.py` | The list is generated from the product files (`<name>-main`, `<name>-uat`); the validator checks the shape and, on the host, equality with the generated list. The `LAKEHOUSE_BUNDLE_REPOSITORY_URL` override is retired. |
| Writers | `scripts/setup/stage-airflow-writers.py` (new) | Stages `writers.json` and the password files for the broker only; `--fingerprint`, `--list`, and `--exclude` for previews. |
| Viewer | `infra/airflow/ensure-broker-viewer.py` (new), `scripts/setup/provision-airflow-secrets.sh`, `compose.airflow.yml` | Read-only Airflow user `lakehouse-broker` (role Viewer), recreated by `airflow-init`; its password secret; the broker's writers mount and Airflow API URL; the fixed single-writer environment and secret removed. |
| Broker | `infra/airflow-token-broker/app.py`, `infra/airflow-token-broker/openapi.yaml` | Per-product writers; product from the DAG ID; Airflow check that the DAG's `bundle_name` is `<product>-<env>` (Viewer token cached); per-writer token checks; registrations keep their product for renewals; 403 `unknown_product`, `unknown_dag`, `bundle_mismatch`; 503 when Airflow cannot answer. |
| Lifecycle | `scripts/lakehouse.sh`, `scripts/setup/airflow-bundle-state.py` (new), `scripts/operations/lib/data-products.sh`, `scripts/operations/create-data-product.sh`, `scripts/operations/remove-data-product.sh`, `scripts/verify/airflow-dags.sh` | `start-airflow` stages the writers, recreates the broker when the fingerprint changed, and records it after the DAG check. Create and remove call `apply_airflow`: unchanged, Airflow stopped, dry run (lists bundles), `--no-restart` (prints the command), or `start-airflow`. The DAG check expects every product bundle. |
| Workload patch | `aidlc-docs/current/deploy/opensource-lakehouse.patch` | For `opensource-lakehouse` at `00b6623`: `<p>-main`/`<p>-uat` give DAG prefix `<bundle>` and envs `prod`/`uat` (legacy names kept); `configs/<product>/<env>.yml` with fallback; `LAKEHOUSE_PRODUCT` in the Spark container; tests and README. Pushed upstream to `main` and `uat` during Build and Test (`e975471`, fix `fedf0bc`). |
| Docs | `README.md` | The `repo` block, bundle naming, writer selection, the workload contract and patch, restarts, two limitations (restarts interrupt runs; public repositories only). The old single-writer limitation is removed. |

## Tests
| Suite | Result |
|---|---|
| `PYTHONPATH=infra/jupyter/hub python3 -m pytest -q tests` | 393 passed, 2 skipped, 1 failed: `test_approved_groups_map_to_exact_airflow_roles` (Airflow role drift, predates this intent) |
| `scripts/verify/broker-unit-tests.sh` (broker image, Python 3.10, pinned FastAPI) | 11 passed, including P4 |
| Workload repository copy, `pytest tests`, `ruff check`, `black --check` | 61 passed, 1 failed (`test_dag_factory_reuses_spark_container_for_bundle_workloads`, already failing upstream after the commit "rename dag"); lint clean |

New tests: `tests/products/test_repo_and_bundles.py` (P1, P2, P3, P5), `tests/airflow/test_token_broker_writers.py` (P4 and refusals; contract tests run on the host), `tests/airflow/test_bundle_lifecycle_contract.py`, the workload `tests/workload_foundation/test_product_bundles.py`. Updated: `tests/keycloak/test_bootstrap_users_contract.py`, the Airflow bundle root tests.

## PBT compliance (partial mode)
| Rule | Status | Notes |
|---|---|---|
| PBT-02 round trip | Compliant | P1 |
| PBT-03 invariants | Compliant | P2, P3, P4, and the workload prefix property |
| PBT-07 generators | Compliant | `tests/products/product_strategies.py`; broker and workload generators inline |
| PBT-08 reproducibility | Compliant | `print_blob=True` on every property |
| PBT-09 framework | Compliant | Hypothesis |

## Deviations from the plan
- Writer staging runs in `start_airflow`, not in `prepare_airflow_environment`, so `airflow-status` and `stop-airflow` never read writer passwords.
- Broker behavioral tests need FastAPI, which the host Python (3.14) cannot install with the pinned versions; they skip on the host and run in the broker image through `scripts/verify/broker-unit-tests.sh`.
- Verified live in Build and Test (see `build-and-test/build-and-test-summary.md`); originally pending: renaming `default`'s bundles in the running Airflow, a test product sharing the repository, and live broker selection and refusal (Build and Test).
