# Intent Summary: Airflow and Broker Python Packages

## Intent
Airflow and Broker Python Packages (`20261113-airflow-python-packages`)

## Objective
Build Airflow on the slim image with only the providers used and fixed Python packages; upgrade the token broker's web stack and cryptography.

## Date
2026-11-13

## Scope
Included: Airflow and broker images, admin/viewer scripts, tests, docs. Excluded: external images, Spark-bundled jars, OpenTelemetry SDK upgrade, Python 3.11.

## Units / workstreams
supply-chain, airflow

## Major requirements
- FR-1 slim base with used providers.
- FR-2 security overrides with pip check.
- FR-3 prek removed; pip/setuptools upgraded.
- FR-4 broker FastAPI/Starlette/cryptography.
- FR-5 platform works.
- FR-6 docs.

## Architecture and design decisions
- Remove unused software rather than patch it: slim base + explicit providers.
- Overrides after the constraints, guarded by pip check.

## Implementation decisions
- httpx2 and graphviz kept for clean CLI JSON; warnings ignored in user-listing scripts.
- pip 26.3 everywhere (vendored msgpack fixed).

## Deviations
- First start-airflow failed at airflow-init (Starlette warning on stdout); Airflow services were down about 20 minutes until fixed.
- dnspython and opentelemetry-api not upgraded (Python 3.11 / SDK pin).

## Verification
construction/build-and-test/build-and-test-summary.md: 667 passed, 3 skipped; image tests 118 and 13; fixable critical 0; live start-airflow, UAT DAG runs, role matrix, SSO login (user); workflow run checked after the push.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra/functional-design/airflow-workflows.md

## Superseded decisions
- Airflow on the full apache/airflow image with providers selected by constraints only.

## Archived artifacts
- aidlc-docs/archive/20261113-airflow-python-packages/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261113-airflow-python-packages/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261113-airflow-python-packages/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261113-airflow-python-packages/full-artifacts/infra/airflow/Dockerfile
- aidlc-docs/archive/20261113-airflow-python-packages/full-artifacts/infra/airflow/requirements.txt
- aidlc-docs/archive/20261113-airflow-python-packages/full-artifacts/infra/airflow/security-overrides.txt
- aidlc-docs/archive/20261113-airflow-python-packages/full-artifacts/infra/airflow/bootstrap-airflow-admin.py
- aidlc-docs/archive/20261113-airflow-python-packages/full-artifacts/infra/airflow/ensure-broker-viewer.py
- aidlc-docs/archive/20261113-airflow-python-packages/full-artifacts/infra/airflow-token-broker/Dockerfile
- aidlc-docs/archive/20261113-airflow-python-packages/full-artifacts/infra/airflow-token-broker/requirements.txt
- aidlc-docs/archive/20261113-airflow-python-packages/full-artifacts/tests/airflow/test_airflow_images.py
- aidlc-docs/archive/20261113-airflow-python-packages/full-artifacts/docs/reference/airflow.md
- aidlc-docs/archive/20261113-airflow-python-packages/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra/functional-design/airflow-workflows.md

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261113-airflow-python-packages/full-artifacts/`
