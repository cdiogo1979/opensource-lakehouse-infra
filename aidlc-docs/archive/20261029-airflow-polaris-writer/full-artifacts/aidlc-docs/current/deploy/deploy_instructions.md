# Deployment Instructions — Airflow Polaris Writer Identity

These are handoff steps. The user subsequently reported completing the image build and successful main and UAT DAG runs; run IDs and revisions were not supplied. This document does not itself authorize deployment or DAG execution.

## 1. Build the Spark runtime image on Airflow's Docker daemon

- **Action and target:** Build `local/lakehouse-spark-runtime:3.5.5_1.10.2` on the same Docker daemon exposed to the Airflow scheduler through its Docker socket.
- **Prerequisites:** Docker Engine and BuildKit available; use the Docker context/daemon mounted by the current Airflow Compose stack. Do not expose or copy secret values.
- **Execution (manual):**

  ```bash
  cd opensource-lakehouse-infra-v2
  docker build -t local/lakehouse-spark-runtime:3.5.5_1.10.2 -f infra/spark-runtime/Dockerfile .
  docker image inspect local/lakehouse-spark-runtime:3.5.5_1.10.2
  ```

- **Validation:** The build succeeds and `docker image inspect` returns the exact tag. It must be visible to the daemon accessed by Airflow; the previous retry failed because this daemon did not have the image. The user reports this build was subsequently completed.
- **Failure handling:** Stop if the build fails or the image is absent from the Airflow-connected daemon. Do not trigger the DAG. No image rollback procedure is specified; retain existing tags and resolve the build/daemon mismatch before retrying.

## 2. Verify Airflow Bundle and DAG availability

- **Action and target:** Confirm the current `main` Bundle exposes `main-init_environment`.
- **Prerequisites:** Existing Airflow services are healthy; workload source commit `da070b6` is pushed to `main`. The configured Bundle refresh interval is 300 seconds.
- **Execution (manual):** From the infrastructure workspace, inspect the Airflow DAG list in the running DAG processor, or wait for the Bundle refresh. The existing helper is `scripts/verify-airflow-environment-dags.sh`; use the environment preparation from `scripts/lakehouse.sh` where needed. Do not restart the currently healthy stack solely for this check.
- **Validation:** `lakehouse-main:main-init_environment` is registered from the expected `main` Bundle revision. Record the observed revision before running. The helper also reports import errors; an existing UAT import error in `notebooks/workload/count_sample_rows.py` is known and must not be interpreted as UAT validation.
- **Failure handling:** Stop before triggering the DAG if the production DAG is not registered at the expected revision. Inspect the DAG processor and Bundle status. Do not alter the two-Bundle configuration.

## 3. Run the approved main production verification

- **Action and target:** Trigger one `main-init_environment` run from the `lakehouse-main` Bundle, using the existing configured sample-table overwrite behavior.
- **Prerequisites:** Steps 1 and 2 pass; production owner confirms the sample-table target is appropriate and authorizes the run. The user reports the main DAG and UAT DAG subsequently completed; their run IDs/revisions are not recorded here.
- **Execution (manual):** Trigger `main-init_environment` once through the Airflow UI or, from the Airflow scheduler container, the CLI below with a unique run ID:

  ```bash
  docker exec lakehouse-local-airflow-scheduler-1 airflow dags trigger main-init_environment --run-id manual__main-writer-verification-<unique-suffix>
  ```

  Record the DAG run ID and Bundle revision. Do not trigger concurrent runs.
- **Validation:** `validate_environment`, `create_cluster`, all workload submissions, `verify_workloads_succeeded`, and `stop_cluster` succeed; logs confirm the configured sample-table write without exposing tokens or identity claims. Confirm no per-run Spark container remains.
- **Failure handling:** Stop additional triggers on any failure. Preserve the run ID and task logs; inspect Docker image availability and container cleanup before retrying. The DAG includes cleanup with `ALL_DONE`, but no data rollback procedure is documented for the sample-table overwrite; treat data recovery as a blocker requiring the data owner’s direction.

## Explicitly unverified / deferred

- UAT was initially out of scope; the user subsequently reports a successful UAT run. Its run ID/revision are not available in this record.
- Concurrent workload, resilience, and live role-matrix tests remain unverified and are not waived as passing.
- A successful designated main run exists for Bundle version `8dcda2d`; the user reports successful later main and UAT runs after building the runtime image, but their IDs/revisions have not been independently recorded.

## Required inputs before any production release

- Named release/data owner and explicit authorization for the sample-table overwrite.
- Confirmed deployment environment, permissions, and maintenance window.
- A data recovery/rollback decision for the sample-table overwrite.
- Resolution or explicit acceptance of the UAT import error if UAT release/runtime validation is required.
