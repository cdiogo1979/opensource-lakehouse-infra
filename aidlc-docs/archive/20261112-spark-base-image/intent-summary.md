# Intent Summary: Spark Base Image

## Intent
Spark Base Image (`20261112-spark-base-image`)

## Objective
Replace the Spark runtime's base image (tabulario/spark-iceberg) with the official Apache Spark image.

## Date
2026-11-12

## Scope
Included: Spark runtime Dockerfile (Spark 3.5.9 official, pinned), maven stage digest, tag rename, Jupyter JDK path, lock generator, tests, docs. Excluded: non-root user, Spark's own jars, the venv's pip/setuptools.

## Units / workstreams
spark-runtime

## Major requirements
- FR-1 official base pinned; maven pinned.
- FR-2 venv from Ubuntu's Python 3.10.
- FR-3 root, compatible entrypoints.
- FR-4 Jupyter JAVA_HOME /opt/java/openjdk.
- FR-5 docs.

## Architecture and design decisions
- Spark 3.5.9 (same Scala and Hadoop client, fixes spark-core CVE).
- Ubuntu's python3.10-venv rather than conda.
- Root kept; non-root as follow-up.

## Implementation decisions
- apt-get upgrade at build for Ubuntu security updates.
- Image tag renamed 3.5.9_1.10.2 in 10 files.
- Lock generator runs the base as root with python3.10-venv.

## Deviations
- None recorded

## Verification
construction/build-and-test/build-and-test-summary.md: 654 passed; parity OK; Trivy 255/3188/8580 -> 23/607/1161; live smoke, role matrix, checkpoints, UAT pipeline, Jupyter.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse-infra/functional-design/workload-python-environment.md

## Superseded decisions
- tabulario/spark-iceberg base; JAVA_HOME /usr/lib/jvm/java-17-openjdk-arm64; venv from /usr/local/bin/python3.

## Archived artifacts
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/infra/spark-runtime/Dockerfile
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/infra/jupyter/singleuser/Dockerfile
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/scripts/setup/lock-workload-python.sh
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/compose.airflow.yml
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/infra/airflow/lakehouse_dags/factory.py
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/scripts/lakehouse.sh
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/scripts/bootstrap/smoke-spark.sh
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/scripts/verify/checkpoint-stream.sh
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/scripts/verify/role-matrix.py
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/scripts/verify/workload-python-parity.sh
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/tests/workload_env/test_image_contracts.py
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/tests/jupyterhub/test_config_contract.py
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/tests/operations/test_compose_modules_contract.py
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/docs/reference/limitations.md
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/docs/reference/workload-python.md
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/README.md
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md
- aidlc-docs/archive/20261112-spark-base-image/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra/functional-design/workload-python-environment.md

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261112-spark-base-image/full-artifacts/`
