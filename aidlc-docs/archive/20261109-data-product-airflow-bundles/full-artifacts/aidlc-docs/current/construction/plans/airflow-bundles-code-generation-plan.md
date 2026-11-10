# Code Generation Plan — airflow-bundles

This plan is the single source of truth for Code Generation. Brownfield: files are changed in place. Files only; Airflow is recreated in Build and Test. The workload patch is created against a copy of the local bundle checkout and is never pushed.

## Unit context
- **Requirements**: FR-1..FR-6 (CR-1).
- **Design**:
  - Application Design C1–C8
  - Functional Design BR-1..BR-6, flows A–D, properties P1–P5
- **PBT (partial)**: Hypothesis.

## Steps

### Step 1 — Product model (C1; FR-1, BR-1)
- [x] `infra/products/data_products.py`: the `Repo` dataclass and validation, `Product.repo`, `bundle_names`, `DAG_ID_PATTERN`, `product_for_dag_id`, and `bundle_config(products)`.
- [x] `infra/products/template.yaml`: a commented `repo` block. `data-products/default.yaml`: the `repo` block for `opensource-lakehouse` (`main`/`uat`).
- [x] `tests/products/product_strategies.py` (generators) and `tests/products/test_repo_and_bundles.py`: P1, P2, P3, P5 plus examples (invalid URLs and branches).

### Step 2 — Bundle list and validator (C2; FR-2, BR-2)
- [x] `scripts/setup/airflow-bundle-config.py`: generate from the product files (the `LAKEHOUSE_BUNDLE_REPOSITORY_URL` override retired).
- [x] `infra/airflow/validate-bundle-config.py`: shape rules for any product set; with `--host-paths`, equality with the generated list.
- [x] Update the existing Airflow bundle tests.

### Step 3 — Writer staging and the broker's Airflow identity (C3, C5; BR-4.1, BR-5)
- [x] `scripts/setup/stage-airflow-writers.py`: `writers.json` plus the password files; the fingerprint.
- [x] `infra/airflow/ensure-broker-viewer.py`; the secret created once (`airflow-broker-viewer-password`); `airflow-init` runs it; compose secret mounts.

### Step 4 — Broker (C4; FR-4, BR-3)
- [x] `infra/airflow-token-broker/app.py`: load the writers; resolve the product from the DAG ID; Airflow bundle check (cached Viewer token); per-writer token issue and checks; registrations bound to their product; reasoned refusals.
- [x] `compose.airflow.yml` (broker): the writers mount, the Viewer password secret, the Airflow API URL; the fixed single-writer environment removed.
- [x] Broker tests (fake Keycloak and Airflow): P4 and the refusals.

### Step 5 — Lifecycle and operators (C6, C7; FR-3, BR-4.2–4.3)
- [x] `scripts/lakehouse.sh`: `start-airflow` stages the writers (moved from `prepare_airflow_environment`, so `airflow-status` and `stop-airflow` never need writer passwords), recreates the broker when the fingerprint changed, and records it (`scripts/setup/airflow-bundle-state.py`) after the DAG check.
- [x] `scripts/operations/lib/data-products.sh`: `apply_airflow` (compare the fingerprint; recreate, print, or dry-run). Called from create and remove.
- [x] `scripts/verify/airflow-dags.sh`: expect each product's bundles; report DAGs per bundle.

### Step 6 — Workload patch (C8; FR-5, BR-6)
- [x] Copy the local checkout of `opensource-lakehouse` (`main`) to the scratchpad; change `dags/dag_defaults.py` and the config loader; run its tests; export `aidlc-docs/current/deploy/opensource-lakehouse.patch` (the deploy handoff).

### Step 7 — Documentation and summary (FR-6)
- [x] `README.md`: the `repo` block, bundle naming, writer selection, the workload contract and patch, restarts.
- [x] Full suite; `aidlc-docs/current/construction/airflow-bundles/code/code-summary.md`.

## Traceability
| Requirement | Steps |
|---|---|
| FR-1 | 1 |
| FR-2 | 1, 2 |
| FR-3 | 5 |
| FR-4 | 3, 4 |
| FR-5 | 6 |
| FR-6 | 1–7 |
