# Unit 2 Code Generation Plan — Airflow Bundle Runner

## Unit Context

- **Unit**: Unit 2 — Airflow Bundle Runner.
- **Stories**: Airflow-triggered, version-pinned Spark workload execution using the existing `write-service-account` identity.
- **Requirements**: Airflow Git Bundle execution, dev-only fail-closed environment selection, maximum two active DAG runs, one ephemeral Spark driver and one worker-only container per run, private credentials/caches, readiness and cleanup deadlines, and no credential values in logs or ordinary Airflow environment variables.
- **Dependencies**: Approved Unit 2 Functional Design, NFR Requirements, NFR Design, Infrastructure Design, and Unit 1 Spark writer runtime contract.
- **Workspace root**: `/Users/carlosdiogo/code_repo/hive-dremio-rustfs` (brownfield).
- **Maintained source**: `/Users/carlosdiogo/code_repo/opensource-lakehouse` (`dags/`, `configs/`, `notebooks/common/`, and `notebooks/workload/`). Adapt this source into the target project; do not copy runtime `.airflow-dag-bundles` caches or archived copies.
- **Service boundary**: Git Bundle DAG source and the Python code Airflow uses to create, ready, submit to, and clean up the per-run driver/worker pair.
- **Identity boundary**: Existing `write-service-account@LAKEHOUSE.LOCAL`, existing writer keytab, and existing RustFS writer credential files. Do not create or rotate identities or secrets.
- **Data boundary**: Dev writes only to `lakehouse_dev.test_database.test_airflow_generated_table` beneath `s3a://lake/warehouse/lakehouse_dev/`. UAT/prod remain disabled and fail closed until explicitly configured.
- **Interface contract**: Remote Spark URL `spark://spark:7077`; shared Hive Metastore `thrift://hive-metastore:9083`; RustFS endpoint `http://object-store:9000`; Bundle path is pinned to the exact revision selected for a DAG run.

This plan is the source of truth for Unit 2 Code Generation. Implement only the listed Bundle/Airflow runner files and the role-specific startup support in the existing Spark entrypoint described below. Do not modify Compose services, Dockerfiles/images, Jenkins pipelines, lakehouse schemas/volumes, or runtime credentials in this unit. Test files and test execution are excluded; verification belongs to the approved integrated Build and Test stage.

## Sequential Generation Steps

### Step 1 — Add the maintained Bundle source to the target project

- [x] Create target directories `dags/`, `configs/`, `notebooks/common/`, and `notebooks/workload/`.
- [x] Bring in and adapt `dags/dag_defaults.py`, `dags/init_environment.py`, and `dags/.airflowignore` from the maintained source repository.
- [x] Bring in and adapt `notebooks/common/__init__.py`, `cli.py`, `config_loader.py`, and `job_runtime.py`.
- [x] Bring in and adapt `notebooks/workload/init_environment.py`, `count_sample_rows.py`, and `jupyter_helper.py`.
- [x] Retain explicit environment validation and DAG dependency-graph validation. Keep the dev workload manual-only and do not make UAT/prod fall back to dev.
- [x] Replace stale Nessie/legacy sample configuration with the approved Hive catalog and RustFS dev prefix. Set the sample table to `lakehouse_dev.test_database.test_airflow_generated_table` and ensure its creation/write occurs as `write-service-account`.
- [x] Keep environment YAML free of credential values. UAT/prod files are disabled and fail closed without configured endpoints and credential references.

### Step 2 — Replace reusable-container execution with a per-run pair lifecycle

- [x] Adapt `dags/dag_factory.py` in place from the maintained source. Keep its workload declaration validation and dependency handling while replacing the single reusable container lifecycle.
- [x] Enforce the approved maximum of two active DAG runs through Airflow DAG/run concurrency configuration before container creation; additional runs queue.
- [x] Derive deterministic, Docker-safe driver and worker names and labels from the DAG/run identity. Restrict discovery, retry cleanup, and removal to that run's labels/pair.
- [x] Create exactly one driver and one worker-only container per admitted run, using the approved Spark image, `iceberg-poc-net`, and shared master `spark://spark:7077`. Do not create or stop another Spark master.
- [x] Mount the exact Bundle revision read-only into the driver. Mount writer keytab, Kerberos configuration, and RustFS writer credential files read-only into both run containers. Pass paths and non-secret settings only.
- [x] Configure each container to acquire its own writer TGT and private ephemeral cache. Preserve separate caches across the pair, runs, long-lived Spark service, and Airflow.
- [x] Implement readiness polling for both containers and worker registration, checking at five-second intervals with a five-minute deadline measured from initial container creation.
- [x] Submit workloads remotely from the driver to the shared Spark master only after pair readiness. Apply the catalog's Hive/S3 settings and use the writer runtime identity.
- [x] Suppress raw Spark exec output and report sanitized phase/status failures.
- [x] Add idempotent run-labeled cleanup. Start worker decommission, stop the driver, inspect worker occupancy, and remove the pair within the shared 60-second budget; report `worker_drain_timeout` when occupancy cannot be confirmed drained before the deadline.
- [x] Preserve shared Spark Standalone placement; executors may run on any registered worker and forced removal may affect another run.

### Step 3 — Add container roles to the existing Spark entrypoint

- [x] Modify `infra/spark/entrypoint.sh` to accept explicit `service`, `driver`, and `worker` roles while preserving current default long-lived `service` behavior and its credential-renewal safeguards.
- [x] In `worker` role, initialize a private writer profile/TGT, start a worker against `spark://spark:7077`, wait for master registration, handle termination, and never start a master/history server/notebook.
- [x] In `driver` role, initialize its own writer profile/TGT, remain available for run-scoped submissions, and never start a master/worker/history server/notebook.
- [x] Keep ephemeral roles fail-closed on required credential paths, file modes, Kerberos authentication, or master/worker readiness. Do not emit credentials or raw output.
- [x] Keep runtime state in private ephemeral tmpfs; do not write tickets or derived AWS credential files to the Bundle, image layer, or persistent volumes.
- [x] Leave the Spark Dockerfile and Compose service unchanged; use only commands/packages in the approved local image.

### Step 4 — Document the Bundle runner contract and write the code summary

- [x] Update target `README.md` with Bundle source layout, dev catalog/table/prefix, writer identity behavior, run-pinned revision, concurrency/readiness/cleanup behavior, and required host-visible credential paths. No credentials are included.
- [x] Create `aidlc-docs/current/construction/unit-2/code/code-summary.md` listing generated/adapted files, traceability, lifecycle behavior, exclusions, and Build and Test gaps.
- [x] Mark implementation steps complete and record the current gate in `aidlc-docs/current/aidlc-state.md`.
- [x] Do not add or run tests during Code Generation. No Compose, Jenkins, image-definition, runtime credential, or lakehouse volume changes were made.

## Build and Test Handoff

The integrated Build and Test stage must verify, without assuming the implementation is correct:

- Bundle loading and immutable revision selection, including retry behavior.
- Two-run concurrency limit and queueing behavior.
- Driver/worker creation, network/DNS reachability, separate TGT caches, worker registration, and five-minute readiness deadline.
- Writer identity access to all three Hive catalogs and the approved RustFS dev prefix; reader denials and StarRocks read-only behavior as specified by the approved matrix.
- Spark remote submission, data landing path/table identifier, and actual table ownership/operations as the writer service account.
- Secret redaction and absence of secret values from Airflow logs, ordinary environment variables, and Bundle contents.
- Idempotent failure cleanup, foreign executor drain observation, forced removal at 60 seconds, and sanitized timeout reporting.
- Fail-closed UAT/prod behavior.

The pinned Spark worker's decommission API and reliable per-worker executor attribution are not established by source presence. If the runner cannot observe/drain safely, Code Generation must report the concrete limitation rather than claiming the approved contract is met.

## Approval Gate

Review this complete plan. Explicit approval is required before any Airflow DAG, Bundle, workload, or README application changes are generated.

**Status**: Original plan and the entrypoint-role scope revision approved on 2026-10-26. Code Generation artifacts are complete; runtime verification is deferred to integrated Build and Test as planned.
