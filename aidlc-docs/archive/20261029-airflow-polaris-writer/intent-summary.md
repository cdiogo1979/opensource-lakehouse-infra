# Intent Summary: Airflow Polaris Writer Identity

## Intent
Airflow Polaris Writer Identity (`20261029-airflow-polaris-writer`)

## Objective
Enable Airflow production and UAT workloads to use the Polaris writer service identity through a private, renewable token flow while preserving the approved Git Bundle setup.

## Date
2026-10-29

## Scope
Airflow writer-token broker and Compose integration; shared Spark 3.5.5 / Iceberg 1.10.2 token-provider runtime; workload integration on main; preserve lakehouse-main/main and lakehouse-uat/uat. Build/test automation and main production E2E were verified. User confirmed the post-build main and UAT DAGs completed. Concurrency, resilience, and live role-matrix testing remain unverified and outside the approved scope.

## Units / workstreams
Airflow writer-token broker and control plane, Shared Spark token provider and runtime, Workload DAG and Spark startup integration, Build, automated test, production verification, and Deploy handoff

## Major requirements
- Use the existing write-service-account / role-default-writer identity for Airflow Spark workloads.
- Keep the writer client secret inside the Airflow broker boundary; deliver only short-lived tokens and run-scoped renewal capability to Spark.
- Preserve the two-Bundle contract lakehouse-main/main and lakehouse-uat/uat.
- Keep Jupyter user identity renewal distinct from Airflow writer identity renewal.
- Retain Polaris authorization and Polaris-vended scoped RustFS credentials.

## Architecture and design decisions
- Use an Airflow-owned private HTTPS broker for per-run writer token acquisition, renewal, and revocation.
- Share the Spark token-provider implementation while selecting separate Jupyter-user and Airflow-writer adapters.
- Use Spark 3.5.5, Java 17, and Iceberg 1.10.2 for the public Iceberg AuthManager API selected in approved Application Design Q5.
- Run the existing main-init_environment workflow with its configured sample-table overwrite.

## Implementation decisions
- Published workload changes to opensource-lakehouse main as da070b6 (Align token provider and workload tests).
- Built and tested Airflow, token-broker, and shared Spark runtime images; verified Compose configuration and automated suites.
- Use one ephemeral Spark container per DAG run with cleanup and broker-state revocation.

## Deviations
- A later retry on da070b6 initially failed at create_cluster because the configured Spark image was absent from Airflow's Docker daemon; the user later reported building the image and successful main and UAT DAG completion.
- The designated successful main E2E run was independently observed against Bundle version 8dcda2d. Later run IDs/revisions were not independently retrievable in the active CLI context and are user-confirmed.
- The active audit was reconstructed from retained state, artifacts, checkpoint, and available transcript excerpts after its working copy was accidentally removed during closure editing; the reconstructed audit explicitly identifies this limitation.

## Verification
Builds, static checks, Compose validation, and automated suites passed; the designated main production run aidlc-writer-verification-20261029T2059Z passed all seven task instances against Bundle version 8dcda2d. The user subsequently reported building the configured image and successfully executing the updated main DAG and UAT DAG; those later run IDs/revisions were not independently retrievable from the active CLI context and are recorded as user-confirmed. Concurrency, resilience, and live role-matrix testing remain unverified and outside the approved verification boundary. No verification waiver is claimed.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse/functional-design/airflow-workload-execution.md

## Superseded decisions
- Earlier Unit 2 text named Iceberg 1.8.1; the approved Q5 choice and implemented runtime use Iceberg 1.10.2.
- The sibling repository's separate three-Bundle guide is not the active v2 contract; the approved two-Bundle contract remains unchanged.

## Archived artifacts
- aidlc-docs/archive/20261029-airflow-polaris-writer/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261029-airflow-polaris-writer/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261029-airflow-polaris-writer/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261029-airflow-polaris-writer/full-artifacts/aidlc-docs/current/compaction/20261029-airflow-polaris-writer/manifest.json
- aidlc-docs/archive/20261029-airflow-polaris-writer/full-artifacts/aidlc-docs/current/aidlc-state.md
- aidlc-docs/archive/20261029-airflow-polaris-writer/full-artifacts/aidlc-docs/current/audit.md
- aidlc-docs/archive/20261029-airflow-polaris-writer/full-artifacts/docker-compose.airflow.yml
- aidlc-docs/archive/20261029-airflow-polaris-writer/full-artifacts/infra/airflow
- aidlc-docs/archive/20261029-airflow-polaris-writer/full-artifacts/infra/spark-runtime
- aidlc-docs/archive/20261029-airflow-polaris-writer/full-artifacts/infra/spark-token-provider
- aidlc-docs/archive/20261029-airflow-polaris-writer/full-artifacts/infra/jupyter/singleuser
- aidlc-docs/archive/20261029-airflow-polaris-writer/full-artifacts/scripts/lakehouse.sh
- aidlc-docs/archive/20261029-airflow-polaris-writer/full-artifacts/scripts/verify-airflow-environment-dags.sh
- aidlc-docs/archive/20261029-airflow-polaris-writer/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/archive/20261029-airflow-polaris-writer/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse/application-design.md
- aidlc-docs/archive/20261029-airflow-polaris-writer/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse/functional-design/airflow-workload-execution.md

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261029-airflow-polaris-writer/full-artifacts/`
