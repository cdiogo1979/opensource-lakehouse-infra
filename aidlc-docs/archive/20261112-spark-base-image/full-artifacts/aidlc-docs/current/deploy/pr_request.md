# PR request — Spark runtime on the official Apache Spark 3.5.9 image

## Problem
The Spark runtime (every Airflow Spark run, and the Spark copied into the Jupyter image) was built on `tabulario/spark-iceberg`, a demo image on Debian 11 with 2022 packages: 255 of the platform's 291 critical findings and 12 023 MEDIUM+ findings, an SSH server and ImageMagick among them. The build stage `maven` was pinned by tag only, and the Jupyter image's `JAVA_HOME` was arm64-specific.

## Solution
- `infra/spark-runtime/Dockerfile`: `apache/spark:3.5.9-scala2.12-java17-python3-ubuntu` pinned by digest, run as root as before, Ubuntu security updates and `python3.10-venv` at build, venv from `/usr/bin/python3` with the unchanged lock; Iceberg 1.10.2, S3A (Hadoop 3.3.4, same as the image) and the token provider as before; `maven` build stage pinned by digest.
- Image tag `local/lakehouse-spark-runtime:3.5.9_1.10.2` everywhere (Compose, factory, scripts, tests).
- Jupyter single-user: copies `/opt/java/openjdk`, `JAVA_HOME=/opt/java/openjdk` (architecture-neutral).
- `scripts/setup/lock-workload-python.sh` resolves the lock in the new base (as root, with venv support).
- Docs: workload Python, limitations, README.

## Verification
Tests 654 passed, 3 skipped; parity OK. Trivy C/H/M 255/3188/8580 -> 23/607/1161. Live: start, Spark smoke checks in all environments, role matrix, streaming checkpoints, UAT `tpch_medallion`, Jupyter Spark read.

## Deployment
`./scripts/lakehouse.sh start` and `start-airflow` (done). Users restart their notebook servers to get the new image.

## Follow-ups
Spark's own vulnerable jars (netty, avro, derby, zookeeper, jackson-mapper-asl: removal of unused ones or Spark 4); running as a non-root user; the venv's pip/setuptools and the glibc 2.31 wheel limit (workload-lock intent).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
