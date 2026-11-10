# Intent Summary: Integrate Airflow, Jenkins, and per-run Spark workloads

## Intent
Integrate Airflow, Jenkins, and per-run Spark workloads (`20261026-integrate-airflow-jenkins-spark`)

## Objective
Integrate the existing Airflow 3 Git DAG Bundle workflow and Jenkins validation pipeline into the Hive/RustFS lakehouse, with ephemeral Spark job containers using the write_service_account identity.

## Date
2026-10-27

## Scope
Integrated Airflow 3.3.2 Git DAG Bundles and per-run Spark driver/worker execution into the local Hive/RustFS/StarRocks Compose PoC. Preserved the main and UAT bundle configuration and configured Spark jobs to use the writer identity. Jenkins hosts the pipeline maintained in opensource-lakehouse; no separate Jenkins job or workload-source copy is maintained in this repository. Deployment was not performed.

## Units / workstreams
Airflow control plane and Git DAG Bundles, Ephemeral Spark workload execution as write_service_account, Jenkins-hosted CI for opensource-lakehouse (no separate hive-dremio-rustfs job), Deployment handoff and verification waiver

## Major requirements
- Retain the two existing Airflow Git DAG Bundles: lakehouse-main tracking main and lakehouse-uat tracking uat, including the repository, connection ID, refresh interval, and sparse directory list.
- Run Spark ETL in ephemeral per-run containers as write_service_account using the existing Kerberos and RustFS credential material.
- Use the Jenkins service for the Airflow/Spark pipeline maintained in opensource-lakehouse; do not create a separate job or duplicate workload source in hive-dremio-rustfs.

## Architecture and design decisions
- Airflow and Jenkins use dedicated persistent metadata/home volumes and dedicated secret files; Hive, RustFS, KDC, JupyterHub, and StarRocks data volumes are preserved.
- Airflow retains exactly two Git Bundles, lakehouse-main and lakehouse-uat; UAT and production workload configurations remain gated as designed.
- Each workload run receives an ephemeral Spark driver/worker pair with shared Spark Standalone scheduling and the approved per-run cleanup contract.
- The connected Jenkins pipeline is sourced from opensource-lakehouse/Jenkinsfile; hive-dremio-rustfs has no separate Jenkins pipeline.

## Implementation decisions
- Use local Airflow and Jenkins images with pinned base images and configured runtime tooling.
- Provision Airflow secret files through the non-rotating helper and keep secret values out of logs and repository configuration.
- The root configs, dags, and notebooks copies were removed; Airflow continues to fetch those sparse directories from opensource-lakehouse into runtime-managed Bundle storage.
- No deployment or opensource-lakehouse workload-source edit was part of this intent.

## Deviations
- Build and Test is partial and closed under the accepted verification waiver.
- The latest recorded Jenkins UAT build failed on an older pipeline revision; the user-reported UAT Airflow DAG success is recorded separately.
- Unit 1-3 Spark renewal/recovery, paired cleanup/decommission, and concurrency behavior remain unverified.
- Deployment was not performed or authorized.

## Verification
The user accepted a verification waiver and directed intent finalization. Jenkins main build #10 passed code-quality stages and 48 unit tests. The latest recorded UAT Jenkins build #2 failed because it checked out an older pipeline revision without pytest; no post-recreation UAT Jenkins rerun was recorded. User-reported production and UAT Airflow DAG runs succeeded. Fresh-home Jenkins plugin reproducibility and Unit 1-3 Spark worker renewal/recovery, per-run cleanup/decommission, and concurrency checks remain unverified. This waiver is not a pass.

## Canonical documents updated
- aidlc-docs/knowledge/hive-dremio-rustfs/application-design.md
- aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/lakehouse-workload-and-access.md

## Superseded decisions
- Earlier project documentation deferred Airflow and Jenkins orchestration; this intent integrates Airflow Bundles and Jenkins hosting for the external workload repository. See archived artifacts.
- An earlier dev-only Bundle proposal was superseded by retaining the sibling project main and uat Bundle configuration.
- A project-local Jenkins validation pipeline and root copies of the workload directories were generated during this intent, then removed after the user confirmed the only workload source is opensource-lakehouse and no separate Jenkins job is wanted.

## Archived artifacts
- aidlc-docs/archive/20261026-integrate-airflow-jenkins-spark/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261026-integrate-airflow-jenkins-spark/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261026-integrate-airflow-jenkins-spark/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261026-integrate-airflow-jenkins-spark/full-artifacts/aidlc-docs/current/compaction/20261026-integrate-airflow-jenkins-spark/manifest.json
- aidlc-docs/archive/20261026-integrate-airflow-jenkins-spark/full-artifacts/README.md
- aidlc-docs/archive/20261026-integrate-airflow-jenkins-spark/full-artifacts/docker-compose.yml
- aidlc-docs/archive/20261026-integrate-airflow-jenkins-spark/full-artifacts/.env.example
- aidlc-docs/archive/20261026-integrate-airflow-jenkins-spark/full-artifacts/infra/airflow
- aidlc-docs/archive/20261026-integrate-airflow-jenkins-spark/full-artifacts/infra/jenkins
- aidlc-docs/archive/20261026-integrate-airflow-jenkins-spark/full-artifacts/infra/spark
- aidlc-docs/archive/20261026-integrate-airflow-jenkins-spark/full-artifacts/scripts/provision-airflow-secrets.sh
- aidlc-docs/archive/20261026-integrate-airflow-jenkins-spark/full-artifacts/scripts/verify-airflow-environment-dags.sh

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261026-integrate-airflow-jenkins-spark/full-artifacts/`
