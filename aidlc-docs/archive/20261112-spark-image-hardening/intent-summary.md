# Intent Summary: Spark Image Hardening and Built-Image Scanning

## Intent
Spark Image Hardening and Built-Image Scanning (`20261112-spark-image-hardening`)

## Objective
Scan the images the platform builds as built, and remove the Spark runtime's compiler toolchain and unused Spark jars.

## Date
2026-11-12

## Scope
Included: Spark runtime Dockerfile, list-images.py targets(), vulnerability-scan.py --build with export scanning, workflow on ubuntu-24.04-arm, tests, docs. Excluded: Airflow image OS and Python fixes, Spark-bundled Netty/Avro/jackson-mapper-asl (upstream), non-root Spark runtime.

## Units / workstreams
supply-chain, spark-runtime

## Major requirements
- FR-1 scan the eight built images on the arm64 runner; external images as pinned; bases and build stages dropped and closed.
- FR-2 purge the toolchain, keep netbase, verify Python, Java, Spark.
- FR-3 remove unused Spark jars with a guard test.
- FR-4 docs.

## Architecture and design decisions
- Targets derived from Compose build blocks and lakehouse.sh docker build lines; source is the Dockerfile's last FROM line.
- Built images scanned from a docker save export, no Docker socket for Trivy.

## Implementation decisions
- hive-storage-api kept for ORC; /opt/spark/yarn removed.
- Export path renamed to the image reference in a new report file (Trivy writes as root on Linux).
- Workflow timeout 120 minutes.

## Deviations
- First workflow run failed on built images (PermissionError); fixed in a second commit after the user pasted the log.
- Test count reported as 663 for the first commit was 661; corrected in the audit.

## Verification
construction/build-and-test/build-and-test-summary.md: 662 passed, 3 skipped; parity OK; Spark smoke Parquet/ORC/Iceberg; live checkpoint-stream, default-uat-test_environment run, Jupyter (user); run 43250207843 failed (PermissionError on built images, fixed in 7944f36); run 43263410488 success; dry-run Spark runtime critical 23 -> 5.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse-infra/functional-design/workload-python-environment.md

## Superseded decisions
- Images built here covered through their bases and the lock (infra-vulnerability-coverage).

## Archived artifacts
- aidlc-docs/archive/20261112-spark-image-hardening/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261112-spark-image-hardening/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261112-spark-image-hardening/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261112-spark-image-hardening/full-artifacts/infra/spark-runtime/Dockerfile
- aidlc-docs/archive/20261112-spark-image-hardening/full-artifacts/scripts/verify/list-images.py
- aidlc-docs/archive/20261112-spark-image-hardening/full-artifacts/scripts/verify/vulnerability-scan.py
- aidlc-docs/archive/20261112-spark-image-hardening/full-artifacts/.github/workflows/vulnerability-scan.yml
- aidlc-docs/archive/20261112-spark-image-hardening/full-artifacts/tests/operations/test_vulnerability_scan.py
- aidlc-docs/archive/20261112-spark-image-hardening/full-artifacts/tests/workload_env/test_image_contracts.py
- aidlc-docs/archive/20261112-spark-image-hardening/full-artifacts/docs/reference/vulnerability-alerts.md
- aidlc-docs/archive/20261112-spark-image-hardening/full-artifacts/docs/reference/workload-python.md
- aidlc-docs/archive/20261112-spark-image-hardening/full-artifacts/docs/future-work.md
- aidlc-docs/archive/20261112-spark-image-hardening/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md
- aidlc-docs/archive/20261112-spark-image-hardening/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra/functional-design/workload-python-environment.md

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261112-spark-image-hardening/full-artifacts/`
