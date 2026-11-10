# Intent Summary: Shared Workload Requirements

## Intent
Shared Workload Requirements (`20261110-shared-workload-requirements`)

## Objective
One pinned Python 3.10 environment for all workload code, identical in Airflow's Spark containers and the Jupyter kernel, plus a product's optional requirements.txt extras constrained by the platform lock in CI, Airflow runs and Jupyter.

## Date
2026-11-10

## Scope
Included: infra/workload-python (requirements.in, generated lock, workload_python.py), the lock generator and parity verifier, the venv in the Spark runtime and Jupyter images, the single Lakehouse (Python 3.10) kernel, lakehouse-install-requirements, the install_requirements DAG task, the CI extras check and lock mount, README, tests; the workload repository's requirements.txt (duckdb==1.5.6), generate_tpch workload and workflow, CI install step and docs (8ef716f, 0bc9ecd, pushed to main and uat). Change requests CR-1 (duckdb instead of pytpch), CR-2 (generate_tpch), CR-3 (broker Viewer token re-sign-in), CR-4 (git and JupyterLab Git in Jupyter), CR-5 (Jupyter extras per session, documented), CR-6 (bundle subdir dags). Excluded: private indexes, caching extras, automatic Jupyter installs, Python or Spark upgrades, JupyterLab's own environment, the enforcing bundle class, the platform Spark session helper (follow-up).

## Units / workstreams
workload-python

## Major requirements
- FR-1/FR-2: infra/workload-python/requirements.in and a generated 53-package lock; /opt/lakehouse/venv (Python 3.10.16) holding exactly the lock in both images, used through PYSPARK_PYTHON; PySpark from /opt/spark.
- FR-3: the only Jupyter kernel is Lakehouse (Python 3.10), named python3.
- FR-4/FR-5: optional root requirements.txt extras, constrained by the lock: install_requirements in each Airflow run (2 retries, 30 s), lakehouse-install-requirements in Jupyter.
- FR-6: image build checks, the CI extras check in lakehouse-validate-workflows, and scripts/verify/workload-python-parity.sh.
- CR-2: workload generate_tpch.py and workflows/generate_tpch.json (eight generate_<entity> tasks, TPC-H counts checked).

## Architecture and design decisions
- One standard-library module (workload_python.py) implements the lock, venv, extras-line and install rules for builds, CI, Airflow and Jupyter.
- Wheels only; CI resolves for the runtime's exact platform tags (CPython 3.10, manylinux2014 and manylinux_2_17 to 2_31 aarch64), because pip accepts only exact --platform tags.
- Airflow extras go into the run container's own venv; Jupyter extras go to ~/.local/lakehouse/python3.10 through a .pth appended after site-packages, installing only the missing set with --no-deps; --reset after a lock change.
- Jupyter Python 3.10.16 from conda-forge, not on PATH; the native kernel is hidden through a jupyter_server_config.d drop-in, keeping the base image's config.
- pyspark, py4j, pip, setuptools and wheel are platform-managed and refused in extras.

## Implementation decisions
- The lock is generated in the runtime's pinned base image by scripts/setup/lock-workload-python.sh and never edited by hand.
- pip freeze for checks runs with PYTHONPATH and PIP_* removed, because /opt/spark/python would otherwise list pyspark.
- The config check calls /opt/lakehouse/venv/bin/python explicitly.
- CR-3: the token broker drops a Viewer token refused with 401 or 403 and retries once.
- CR-6: GitDagBundle subdir dags in BUNDLE_KWARGS and validate-bundle-config.py; the stub still reads the whole checkout.

## Deviations
- CR-1: pytpch 0.2.0 has only an x86_64 glibc 2.34 wheel; duckdb==1.5.6 is the example extra.
- sparse_dirs did not change: cone mode always checks out root files such as requirements.txt.
- The eight generate_tpch tasks run in parallel and each downloads DuckDB's tpch extension; probed safe, unlike the planned single cached download.
- CR-4: git and jupyterlab-git 0.55.0 added to the Jupyter image during Build and Test.
- Operational: JupyterHub had loaded an older data_products.py and admitted only platform admins; fixed by a restart (follow-up recorded).

## Verification
See construction/build-and-test/build-and-test-summary.md. Host 517 passed, 3 skipped; Airflow image 51 passed; broker image 13 passed; workload repository 51 passed with DuckDB, lint clean. Live: both images built with lock checks, parity OK; default-uat-test_environment 8/8 without extras; default-uat-generate_tpch 13/13 with duckdb==1.5.6 and all eight TPC-H counts (also after CR-6); a run after start-airflow without a broker restart (403, re-sign-in, 200); DAG processor parses only dags/lakehouse.py; Jenkins default_ci main #3 and uat #3 SUCCESS with the extras check; user-confirmed JupyterHub kernel, git clone, extras command and notebook. Not run: a production generate_tpch run; a CI refusal of a pushed invalid requirements.txt.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/airflow-workflows.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/jenkins-ci-access.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/workload-python-environment.md

## Superseded decisions
- Workload code on the Spark base image's 146 unpinned packages (and Python 3.13 in Jupyter) replaced by the shared locked venv; see archive requirements.md.
- FR-5 'persisted in the user's home' replaced by CR-5: Jupyter extras last one server session, because only ~/work is a volume.
- FR-4's sparse_dirs change replaced by no change (root files are always checked out); bundles without subdir replaced by subdir dags (CR-6).

## Archived artifacts
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/aidlc-docs/current/compaction/20261110-shared-workload-requirements/manifest.json
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/airflow-workflows.md
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/jenkins-ci-access.md
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/infra/workload-python/requirements.in
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/infra/workload-python/requirements.lock
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/infra/workload-python/workload_python.py
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/scripts/setup/lock-workload-python.sh
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/scripts/verify/workload-python-parity.sh
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/infra/spark-runtime/Dockerfile
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/infra/jupyter/singleuser/Dockerfile
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/infra/jupyter/singleuser/requirements.txt
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/infra/jupyter/singleuser/kernel.json
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/infra/jupyter/singleuser/lakehouse-kernels.json
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/infra/jupyter/singleuser/lakehouse-user-extras.pth
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/infra/jupyter/singleuser/lakehouse-install-requirements
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/infra/airflow/lakehouse_dags/factory.py
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/infra/products/data_products.py
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/infra/airflow/validate-bundle-config.py
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/infra/airflow-token-broker/app.py
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/infra/jenkins/bin/lakehouse-validate-workflows
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/compose.jenkins.yml
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/README.md
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/tests/workload_env/test_workload_python.py
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/tests/workload_env/test_workload_python_properties.py
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/tests/workload_env/test_image_contracts.py
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/tests/airflow/test_dag_factory.py
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/tests/airflow/test_workflow_spec.py
- aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/tests/airflow/test_token_broker_writers.py

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261110-shared-workload-requirements/full-artifacts/`
