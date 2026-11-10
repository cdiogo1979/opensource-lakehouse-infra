# Workload Repository Airflow Integration

The `opensource-lakehouse` repository supplies DAGs, configuration, and workload entrypoints consumed by the v2 Airflow Git Bundles. The active deployment contract is `lakehouse-main` tracking `main` and `lakehouse-uat` tracking `uat`; do not replace it with a different Bundle layout without an approved scope change.

Airflow creates an ephemeral Spark container per DAG run and mounts the selected Bundle checkout read-only. Workload Spark startup selects the Airflow adapter in the shared Spark 3.5.5 / Iceberg 1.10.2 runtime. It uses a short-lived access token and run-scoped broker capability to authenticate to Polaris as the existing `write-service-account` / `role-default-writer` identity. The writer secret remains in the broker/Airflow boundary. Polaris continues to vend scoped RustFS credentials.

Jupyter Spark shares the provider implementation but selects a separate user-bound Hub broker adapter; Airflow and Jupyter identities and capabilities are not interchangeable. The writer service changes were pushed to `main` as `da070b6`.

The designated production workflow is `main-init_environment`, with its configured sample-table overwrite. Build/test suites and the designated main run passed. The user subsequently reported successful main and UAT DAG execution after building the image; these later runs are user-confirmed but their run IDs/revisions were not independently available in the active CLI session. Concurrent workloads, resilience, and live role-matrix checks remain unverified.

Detailed intent history: `aidlc-docs/archive/20261029-airflow-polaris-writer/`.
