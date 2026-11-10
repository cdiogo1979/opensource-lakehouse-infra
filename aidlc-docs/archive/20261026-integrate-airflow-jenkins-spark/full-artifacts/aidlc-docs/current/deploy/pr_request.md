# PR Request: Integrate Airflow Spark Workloads with the Hive/RustFS Lakehouse

## Problem

Airflow-created Spark job containers need to authenticate to Hive Metastore with the Kerberos `write-service-account` principal and access the RustFS objects used by the lakehouse workload. The existing RustFS writer policy was limited to two warehouse database prefixes, which denied access to the workload's environment-specific paths in the `lake` bucket.

## Solution

The writer identity now receives list, read, write, delete, and multipart actions across the complete `lake` bucket. Other identities retain their existing prefix-scoped policies. Dev, UAT, and production workload storage paths end in `/`, allowing the workload to append the table name without malformed object paths. The existing Airflow Git Bundle list and run-pinned bundle behavior remain unchanged.

## Main changes

- `infra/identity-provisioner/provision-rustfs-identities.py` — builds and reconciles a bucket-wide `lakehouse-writer` policy, verifies the exact policy after update, and checks full-bucket listing with the existing writer credentials.
- `configs/dev.yml`, `configs/uat.yml`, `configs/prod.yml` in the `opensource-lakehouse` project — normalize storage prefixes with a trailing slash.
- `notebooks/common/job_runtime.py` and the Airflow/Spark integration files — use the writer keytab and credentials in the per-run Spark workload, as described in the approved unit summaries.

## Verification

- The user reports all tests are fine after the writer-policy change; detailed external test output was not supplied.
- RustFS provisioning reported `lakehouse-writer: updated and exact`; the existing writer identity could list the complete bucket. `ROTATE_RUSTFS_WRITER_SECRET` was explicitly false.
- Prior Unit 4 checks passed Compose validation, local image builds, Python/Bash source validation, and production/UAT DAG registration.
- Build and Test remains **partial**. The Jenkins Declarative Pipeline Linter returned HTTP 403; no trusted Pipeline-from-SCM build was run because the target SCM URL/ref were not supplied. The Airflow DAG processor reported a `SystemExit: 2` import warning for `count_sample_rows.py`, although expected DAG IDs registered. Integrated Unit 1–3 acceptance evidence is not recorded as complete.
- No full intent verification or verification waiver is claimed.

## Deployment

Operational steps are required. See [`deploy_instructions.md`](deploy_instructions.md). This handoff does not deploy changes, trigger DAGs, or create a pull request.

## Risks and limitations

- The writer can read, overwrite, and delete any object in `lake`; this is broader than prefix isolation and is intended for the ETL service identity only. Keep the writer keytab and RustFS secret limited to trusted Spark jobs.
- Jenkins trusted SCM admission and the Pipeline validation build remain unverified. The required repository URL and protected ref are deployment inputs.
- The Airflow notebook import warning and integrated Unit 1–3 acceptance checks remain open. Do not infer release readiness from DAG registration alone.
- Confirm the desired UAT and production execution gates before enabling or triggering those workloads.
