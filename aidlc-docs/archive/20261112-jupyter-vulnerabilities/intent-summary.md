# Intent Summary: Jupyter Vulnerabilities

## Intent
Jupyter Vulnerabilities (`20261112-jupyter-vulnerabilities`)

## Objective
Close the vulnerabilities reported for the Jupyter images (JupyterHub and the single-user server).

## Date
2026-11-12

## Scope
Included: base digests 6.1.1-7, Lab/notebook pins removed with a constrained install, apt upgrade, tests, docs. Excluded: Spark jars (Spark base intent), pyarrow and the venv's pip/setuptools (workload-lock intent).

## Units / workstreams
jupyter

## Major requirements
- FR-1 6.1.1-7 digests.
- FR-2 no Lab/notebook pins, guarded.
- FR-3 residual patches (apt).
- FR-4 platform works (user live check).
- FR-5 docs.

## Architecture and design decisions
- Same JupyterHub version rebuilt rather than 6.2.0.
- Base's JupyterLab/notebook kept; install constrained to them.

## Implementation decisions
- pip list --format=freeze (pip freeze shows conda packages as 'name @ file://').
- Targeted apt --only-upgrade.

## Deviations
- The Spark runtime image was missing locally and was rebuilt.
- The user ran the live check.

## Verification
construction/build-and-test/build-and-test-summary.md: Trivy 40 -> 7 and 9 -> 1 packages; 653 passed, 3 skipped; parity OK; live check by the user.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md

## Superseded decisions
- jupyterlab==4.3.5 and notebook==7.3.2 pins; arm64-only Jupyter digests.

## Archived artifacts
- aidlc-docs/archive/20261112-jupyter-vulnerabilities/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261112-jupyter-vulnerabilities/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261112-jupyter-vulnerabilities/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261112-jupyter-vulnerabilities/full-artifacts/infra/jupyter/hub/Dockerfile
- aidlc-docs/archive/20261112-jupyter-vulnerabilities/full-artifacts/infra/jupyter/singleuser/Dockerfile
- aidlc-docs/archive/20261112-jupyter-vulnerabilities/full-artifacts/infra/jupyter/singleuser/requirements.txt
- aidlc-docs/archive/20261112-jupyter-vulnerabilities/full-artifacts/tests/workload_env/test_image_contracts.py
- aidlc-docs/archive/20261112-jupyter-vulnerabilities/full-artifacts/docs/reference/jupyterhub.md
- aidlc-docs/archive/20261112-jupyter-vulnerabilities/full-artifacts/docs/reference/limitations.md
- aidlc-docs/archive/20261112-jupyter-vulnerabilities/full-artifacts/README.md
- aidlc-docs/archive/20261112-jupyter-vulnerabilities/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261112-jupyter-vulnerabilities/full-artifacts/`
