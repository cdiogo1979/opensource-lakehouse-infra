# Intent Summary: Data Product Airflow Bundles

## Intent
Data Product Airflow Bundles (`20261109-data-product-airflow-bundles`)

## Objective
Each data product can name its DAG repository (repo: url, prod_branch, uat_branch; read anonymously). The platform creates the Airflow bundles <name>-main and <name>-uat from it, registers them when a product is created, and runs each product's DAGs as that product's writer, chosen from the DAG-ID prefix and confirmed against Airflow's bundle_name by the token broker.

## Date
2026-11-09

## Scope
Included: the repo block in the product model and template; default's repo (opensource-lakehouse main/uat); bundle-list generation and validation; per-product writer staging and the broker's read-only Airflow Viewer; the per-product token broker with reasoned refusals; Airflow recreation from start-airflow and the product commands (fingerprint); the per-bundle DAG check; the workload patch for opensource-lakehouse (pushed to main and uat on the user's instruction); README and tests. Excluded: per-product Airflow permissions; avoiding the Airflow restart (discussed, not adopted); credentials for private repositories.

## Units / workstreams
airflow-bundles

## Major requirements
- FR-1: optional repo block (url, prod_branch, uat_branch) in the product file; credential-free https; default uses opensource-lakehouse main/uat.
- FR-2: Airflow bundles <name>-main and <name>-uat generated from the product files and validated.
- FR-3: creating or removing a product with a repo registers or drops its bundles (Airflow recreated when changed and running).
- FR-4: runs write as the product's writer, derived from the DAG-ID prefix and confirmed against Airflow's bundle_name; no credentials in Airflow DAG code.
- FR-5: workload repositories name DAGs <bundle>-<workload> (patch for opensource-lakehouse), with optional configs/<product>/<env>.yml.
- CR-1: no writer field in the YAML; the writer is the product's writer_user.

## Architecture and design decisions
- Writer selection by DAG-ID prefix plus an Airflow API check of bundle_name as a read-only Viewer (lakehouse-broker), instead of Airflow connections or secrets visible to DAG code.
- Bundle names use the data product name from the YAML (<name>-main, <name>-uat), not the repository name; default's bundles renamed now.
- Register and load on create: the product commands recreate Airflow when the bundle/writer fingerprint changed and Airflow is running; --no-restart prints the command.
- Repositories are read anonymously; several products may share one.
- The workload patch is prepared here and applied in the workload repository; on the user's instruction it was pushed to main and uat (e975471, fedf0bc).
- Airflow restart on product changes kept as a documented limitation (Airflow 3.3 reads the bundle list once per process); broker hot reload, a single local platform bundle, and other orchestrators were discussed and not adopted.
- Extensions: PBT partial (PBT-02, 03, 07, 08, 09), Security and Resiliency off.

## Implementation decisions
- data_products: Repo dataclass, bundle_config, bundle_names, DAG_ID_PATTERN, product_for_dag_id; broker repeats the pattern, checked by a contract test.
- stage-airflow-writers.py stages writers.json and password files for the broker only and prints a fingerprint; --fingerprint/--list/--exclude for previews; airflow-bundle-state.py records it.
- Broker: 403 unknown_product, unknown_dag, bundle_mismatch; 503 when Airflow cannot answer; Viewer token cached until 60 s before expiry; registrations keep their product.
- Writer staging runs in start-airflow, not prepare_airflow_environment, so status and stop never need writer passwords.
- Broker behavioral tests run inside the broker image (scripts/verify/broker-unit-tests.sh) because the pinned FastAPI does not install on the host Python 3.14.

## Deviations
- The workload patch was pushed by the AI to main and uat on explicit user instruction, after the user first chose to apply it themselves.
- Build and Test found that a comment in the patch made Airflow parse notebooks/common/job_runtime.py as a DAG file; fixed in fedf0bc.
- Before the patch, both renamed bundles built the same dev-test_environment DAG ID and start-airflow's check timed out; README now states the dependency.

## Verification
See construction/build-and-test/build-and-test-summary.md. Suite 393 passed, 2 skipped, 1 pre-existing failure (Airflow developer-role drift); broker tests in its image 11 passed (P4); workload repository 61 passed, 1 upstream failure. Live: default-main/default-uat registered and fingerprint recorded; Viewer only; per-product writer selection (srv-default-writer, srv-bttest-writer), renewal, revoke; unknown_product and unknown_dag refusals; UAT DAG run succeeded end to end; test product bttest created, re-applied (unchanged), and removed with Airflow recreated. bundle_mismatch verified by unit tests only.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md

## Superseded decisions
- Fixed bundles lakehouse-main/lakehouse-uat replaced by per-product <name>-main/<name>-uat (default-main/default-uat).
- Single writer srv-default-writer in the broker (KEYCLOAK_WRITER_USERNAME/KEYCLOAK_WRITER_PASSWORD_FILE, srv_default_writer_password secret) replaced by per-product writers from the staged list.
- LAKEHOUSE_BUNDLE_REPOSITORY_URL override retired; the repository comes from each product's repo block.
- 'New products need no restart except Jenkins' replaced by: Airflow is recreated when bundles or writers change.

## Archived artifacts
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/aidlc-docs/current/compaction/20261109-data-product-airflow-bundles/manifest.json
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/infra/products/data_products.py
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/infra/products/template.yaml
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/data-products/default.yaml
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/scripts/setup/airflow-bundle-config.py
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/infra/airflow/validate-bundle-config.py
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/scripts/setup/stage-airflow-writers.py
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/scripts/setup/airflow-bundle-state.py
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/infra/airflow/ensure-broker-viewer.py
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/scripts/setup/provision-airflow-secrets.sh
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/compose.airflow.yml
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/infra/airflow-token-broker/app.py
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/infra/airflow-token-broker/openapi.yaml
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/scripts/lakehouse.sh
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/scripts/operations/lib/data-products.sh
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/scripts/operations/create-data-product.sh
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/scripts/operations/remove-data-product.sh
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/scripts/verify/airflow-dags.sh
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/scripts/verify/broker-unit-tests.sh
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/README.md
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/tests/products/product_strategies.py
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/tests/products/test_repo_and_bundles.py
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/tests/airflow/test_token_broker_writers.py
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/tests/airflow/test_bundle_lifecycle_contract.py
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/tests/keycloak/test_bootstrap_users_contract.py
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/tests/airflow/test_bundle_root_contract.py
- aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/tests/conftest.py

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261109-data-product-airflow-bundles/full-artifacts/`
