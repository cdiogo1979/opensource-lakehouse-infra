# Unit 2 Functional Design Plan — Airflow Bundle Runner

## Unit Context

- **Unit**: Unit 2 — Airflow Bundle Runner.
- **Stories**: US-01, US-02, US-03, US-04, and US-06, with US-03 supported by Units 1 and 3.
- **Requirements**: FR-2, FR-3, FR-4, FR-7, NFR-1, NFR-2, NFR-3, and NFR-4.
- **Dependency**: Unit 1's approved Spark writer contract. The service endpoint is specified as `spark://spark:7077`; its live standalone worker registration remains unverified in the Unit 1 checkpoint and must be proven before Unit 2 runtime integration is accepted.
- **Maintained source**: `../opensource-lakehouse/` is the maintained bundle repository. `../airflow-spark-jenkins/.airflow-dag-bundles/` is runtime checkout/cache state and must not be copied as the canonical source.
- **Workspace root**: `/Users/carlosdiogo/code_repo/hive-dremio-rustfs` (brownfield).
- **Ownership boundary**: Existing Git Bundle contract, DAG factory, DAG declarations, environment selection, and workload invocation behavior. Compose service integration belongs to Unit 3.
- **Writer identity**: Reuse `write-service-account@LAKEHOUSE.LOCAL` and its existing keytab/RustFS credentials; no credential rotation or new principal.

This plan defines detailed, technology-agnostic business behavior for a run-pinned Airflow bundle and its per-run ephemeral Spark driver/worker pair. It does not add Compose services, configure credential mounts, or implement source files in this stage.

## Sequential Design Steps

### Step 1 — Confirm current bundle behavior and contracts

- [x] Review the approved Unit 2 boundary, story map, current requirements, and application-design contracts.
- [x] Inspect the maintained `../opensource-lakehouse/` source for DAG declarations, the shared factory, bundle/environment mapping, workload behavior, and the selected example workload.
- [x] Keep the runtime `.airflow-dag-bundles` clone/cache out of the source-of-truth set.
- [x] Reconcile source behavior with the approved requirements: immutable run-pinned bundle, remote Spark execution, writer identity, explicit environment selection, and cleanup on all outcomes.

### Step 2 — Define the run workflow and domain model

- [x] Define the relationship among bundle identity, pinned commit, environment configuration, Airflow DAG run, workload graph, ephemeral driver, writer credential references, and run result.
- [x] Model run states from bundle resolution through config validation, driver preparation, workload execution, result reporting, and cleanup.
- [x] Define how independent workloads run in parallel and how `runs_after` dependencies determine ordering.

### Step 3 — Define environment selection and input validation

- [x] Specify how the stable bundle identity selects one environment config for the whole run.
- [x] Define validation before driver creation for supported environment, required config fields, valid workload declarations, and dependency graphs.
- [x] Ensure unconfigured UAT/production fail before driver creation and cannot fall back to local development.
- [x] Preserve the selected bundle revision across config, DAG, helper modules, and workload files for every task in the run.

### Step 4 — Define driver and writer execution behavior

- [x] Define one ephemeral driver per DAG run, reused for that run's declared Spark tasks and removed after all tasks settle.
- [x] Specify obtaining and validating the existing writer TGT before submission, private per-run cache behavior, and driver access to the read-only bundle and file-backed writer credentials.
- [x] Specify submission to Unit 1's remote Spark master using the target Hive/Iceberg and RustFS Spark configuration; local-only Spark execution is out of contract.
- [x] Define task results and safe diagnostic reporting without credential values or ticket material.

### Step 5 — Define failures, cleanup, and repeat behavior

- [x] Define the Airflow-visible result for invalid bundle/config/workload, Docker create/start errors, Kerberos failure, Spark submit failure, workload failure, and driver cleanup failure.
- [x] Ensure driver cleanup is attempted after successful and failed tasks, including when environment validation or driver startup fails.
- [x] Define how cleanup handles an already absent driver and how the original workload failure remains visible if cleanup also fails.
- [x] Preserve the pinned bundle and all persistent lakehouse volumes/data during retry and cleanup.
- [x] Retain the existing workload contract of overwriting only its dedicated synthetic sample table; no unrelated table is modified.

### Step 6 — Generate the Unit 2 Functional Design artifacts

- [x] Create `aidlc-docs/current/construction/unit-2/functional-design/business-logic-model.md`.
- [x] Create `aidlc-docs/current/construction/unit-2/functional-design/business-rules.md`.
- [x] Create `aidlc-docs/current/construction/unit-2/functional-design/domain-entities.md`.
- [x] Keep these as active intent artifacts; canonical knowledge changes remain deferred to approved intent closure.

## Resolved Clarification

The maintained bundle repository's current `configs/dev.yml` targets the legacy `lakehouse_dev` namespace and `s3a://lake/opensource-lakehouse/dev/`. The target currently has one Hive-backed Iceberg catalog and existing sample namespaces `databaseA` and `databaseB`. The clarification now requests three Hive catalogs in the local metastore; UAT/prod Airflow environments nevertheless remain unavailable until their real endpoints and credentials are configured.

The clarifications establish three Hive catalogs (`lakehouse_dev`, `lakehouse_uat`, `lakehouse_prod`), each containing the existing `databaseA` and `databaseB` namespaces; writer/admin access across all catalogs and their object storage; equivalent read-only access for `user_a` and `user_b`; a dev workload target of `lakehouse_dev.test_database.test_airflow_generated_table`; and one ephemeral worker per run with shared Spark Standalone scheduling. See both Unit 2 clarification files for the recorded decisions and assumptions.

## Approval Gate

The Functional Design was revised from the worker-topology clarification to include one ephemeral worker per DAG run. Review its current artifacts together with the Unit 2 NFR Requirements artifacts before approving the revised baseline and proceeding to Unit 2 NFR Design.
