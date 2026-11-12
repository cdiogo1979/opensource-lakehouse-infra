# Requirements — Spark Base Image

Depth: standard (the runtime of every Airflow Spark run and of Jupyter's Spark).

## Request
Replace `tabulario/spark-iceberg` (a demo image on Debian 11: 255 of the platform's 291 critical findings, 12 023 MEDIUM+ findings) with the official Apache Spark image.

## Answers
- Spark **3.5.9**: `apache/spark:3.5.9-scala2.12-java17-python3-ubuntu@sha256:f3d6eaa8bab8ec2e38f3c3918a5b2f8b253c95bcb19f9e87ad0e0cdacf9df2d5` (multi-arch, 2026-07-24).
- Workload venv from **Ubuntu's Python 3.10** (`python3.10-venv` from apt).
- User: **root, as now**; running as `spark` (uid 185) is a follow-up.

## Functional requirements
- **FR-1** `infra/spark-runtime/Dockerfile` builds from the official image; the build stage `maven:3.9.9-eclipse-temurin-17` is pinned by digest (`sha256:f58d59b6...318cc`); Iceberg 1.10.2 (`iceberg-spark-runtime-3.5_2.12`, `iceberg-aws-bundle`), the token provider and the S3A jars (`hadoop-aws` 3.3.4, `aws-java-sdk-bundle` 1.12.262; the image's Hadoop client is 3.3.4) are added as today; `spark-defaults.conf` unchanged.
- **FR-2** The workload venv `/opt/lakehouse/venv` is built from `/usr/bin/python3` (3.10) with the lock, checked by `check-venv`; `PYSPARK_PYTHON` and `PYSPARK_DRIVER_PYTHON` point at it, as now.
- **FR-3** The image runs as root (`USER root`), keeps an entrypoint compatible with Airflow's run containers (the factory passes its own) and with `smoke-spark.sh`, `role-matrix.py`, `checkpoint-stream.sh`.
- **FR-4** The Jupyter single-user image copies the JDK from `/opt/java/openjdk` and sets `JAVA_HOME=/opt/java/openjdk` (architecture-neutral; removes the arm64 `JAVA_HOME` limitation); it keeps `/opt/spark`.
- **FR-5** Docs: workload Python, limitations (the arm64 JDK path entry removed; the aarch64 wheel tags remain), Spark versions where documented.

## Non-functional and checks
- **NFR-1** Tests and contracts updated; `workload-python-parity.sh` passes (same 56 packages in both images).
- **NFR-2** Live (with approval): `start` and `start-airflow` with the new image, the product bootstrap's Spark smoke check, `role-matrix.py`, `checkpoint-stream.sh`, a UAT `tpch_medallion` run, and a Jupyter Spark read.
- **NFR-3** Trivy before and after for the Spark runtime and the single-user image.

## Known follow-ups
- The venv's pip and setuptools come from the interpreter's bundled wheels (old); pinning them is part of the workload-lock intent.
- Running the Spark runtime as a non-root user.
