# PR Request — Data product Airflow bundles

_Proposed PR description. No pull request has been created; this workspace has no git metadata. The companion workload change is already on `main` and `uat` of `cdiogo1979/opensource-lakehouse` (`e975471`, `fedf0bc`), pushed on the user's instruction._

## Problem
Airflow had two fixed Git bundles (`lakehouse-main`, `lakehouse-uat`) from one repository, and its token broker wrote only as `srv-default-writer`. A new data product could not bring its own DAG repository, and its runs could not write as the product's own writer.

## Solution
- **`repo` block in the product file** (optional): `url` (credential-free `https`, read anonymously), `prod_branch`, `uat_branch`. `default` uses `opensource-lakehouse` (`main`/`uat`).
- **Bundles generated from the product files**: `<name>-main` (prod branch) and `<name>-uat` (UAT branch) for every product with a repo; validated on the host against the generated list.
- **Writer derived from the DAG ID, no YAML field (CR-1)**: DAG IDs start with their bundle name (`default-main-test_environment`). The broker takes the product from that prefix, confirms through the Airflow API as the read-only Viewer `lakehouse-broker` that the DAG's `bundle_name` is that product's bundle, and only then issues the product's writer token (checking the username and the writer group). Refusals: `unknown_product`, `unknown_dag`, `bundle_mismatch`; 503 when Airflow cannot answer.
- **Credentials stay out of Airflow**: writer passwords are staged only for the broker (read-only mount); DAG code and Spark never see them.
- **Lifecycle**: `start-airflow` stages the writers, recreates the broker when the bundle/writer fingerprint changed, and records it after the DAG check. Product create and remove recreate Airflow only when the fingerprint changed and Airflow is running (`--no-restart` prints the command, `--dry-run` lists the bundles).
- **Workload contract** (patch in `opensource-lakehouse`): `<p>-main`/`<p>-uat` give the DAG prefix `<bundle>` and the `prod`/`uat` configs (legacy `lakehouse-*` kept); per-product configs `configs/<product>/<env>.yml` with fallback.
- **Decisions**: DAG-ID prefix plus Airflow check; data product `name` as the prefix; rename `default`'s bundles now; register and load on create; the user prepares (here: approved the push of) the workload patch; no writer field (CR-1). Extensions: PBT partial.

## Main changes
| Area | Paths |
|---|---|
| Product model | `infra/products/data_products.py`, `infra/products/template.yaml`, `data-products/default.yaml` |
| Bundle list | `scripts/setup/airflow-bundle-config.py`, `infra/airflow/validate-bundle-config.py` |
| Writers and Viewer | `scripts/setup/stage-airflow-writers.py` (new), `scripts/setup/airflow-bundle-state.py` (new), `infra/airflow/ensure-broker-viewer.py` (new), `scripts/setup/provision-airflow-secrets.sh`, `compose.airflow.yml` |
| Broker | `infra/airflow-token-broker/app.py`, `infra/airflow-token-broker/openapi.yaml` |
| Lifecycle | `scripts/lakehouse.sh`, `scripts/operations/lib/data-products.sh`, `scripts/operations/{create,remove}-data-product.sh`, `scripts/verify/airflow-dags.sh`, `scripts/verify/broker-unit-tests.sh` (new) |
| Docs and tests | `README.md`; `tests/products/{product_strategies,test_repo_and_bundles}.py`, `tests/airflow/{test_token_broker_writers,test_bundle_lifecycle_contract}.py` (new); updated Keycloak and Airflow bundle tests |
| Workload patch | `aidlc-docs/current/deploy/opensource-lakehouse.patch` (= `00b6623..fedf0bc`) |

## Verification
- **Suite**: `PYTHONPATH=infra/jupyter/hub python3 -m pytest -q tests`: 393 passed, 2 skipped, 1 failed (pre-existing Airflow developer-role drift).
- **Broker** (`scripts/verify/broker-unit-tests.sh`, in its image): 11 passed, including P4.
- **Workload repository**: 61 passed, ruff and black clean; 1 upstream failure (stale DAG-name assertion).
- **Live**: bundles `default-main`/`default-uat` registered and checked; Viewer only; per-product writer selection (`srv-default-writer`, `srv-bttest-writer`), renewal, revoke; `unknown_product` and `unknown_dag` refusals; end-to-end UAT run (7 of 7 tasks); test product `bttest` created (Airflow recreated), re-applied (unchanged), and removed (Airflow recreated, writer unstaged).
- **Not run live**: `bundle_mismatch` (no real DAG can produce it; unit-tested), a production DAG run, `bttest` DAG runs.

## Deployment
Required: see [deploy_instructions.md](deploy_instructions.md). On this local stack every step has already been done during Build and Test.

## Risks and limitations
- **Workload repositories must follow the contract**: without the patch, both bundles build the same `dev-...` DAG ID, one bundle shows no DAG, and `start-airflow`'s check fails. DAGs whose IDs lack the bundle prefix get no writer token.
- **Restarts interrupt runs**: bundle or writer changes recreate the Airflow containers; use `--no-restart` and run `start-airflow` when idle.
- **Public repositories only**: bundles are read without credentials.
- **Staged writer passwords** are 0644 files under `.runtime/container-mounts/airflow-writers/`, protected by the 0700 `.runtime` directories; only the broker mounts them.
- **Platform-wide Airflow roles**: unchanged; a product's Airflow rights still apply to all of Airflow.
- **Legacy DAG records**: renamed bundles leave stale DAG records (here `dev-test_environment`) until deleted; the broker refuses them.
