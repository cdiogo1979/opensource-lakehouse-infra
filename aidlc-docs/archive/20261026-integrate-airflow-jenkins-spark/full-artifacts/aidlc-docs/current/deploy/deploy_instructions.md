# Deployment Instructions

These steps describe the local Compose deployment. They do not authorize a production release. Stop if any prerequisite or validation fails.

## 1. Prepare the source revisions

1. Merge the approved `opensource-lakehouse` changes to the refs consumed by Airflow Bundles (`main` and `uat`) using the repository's normal review process. Preserve the configured `lakehouse-main` and `lakehouse-uat` Bundle entries.
2. Confirm the checked-in dev, UAT, and production `storage_path` values end with `/` and point to their approved prefixes in the `lake` bucket.
3. Obtain the Jenkins SCM repository URL and protected ref from the maintainer. These values are currently unknown. Configure the Jenkins Pipeline-from-SCM job with script path `Jenkinsfile`, maintainer-only configuration/trigger access, and any private SCM credential through Jenkins Credentials. Do not use untrusted branch or pull-request execution.

## 2. Apply the RustFS identity policy

From the `hive-dremio-rustfs` project root, ensure the local Compose prerequisites and file-backed secrets have already been provisioned. Set the host path variables documented in `README.md` (`LAKEHOUSE_PROJECT_ROOT`, `LAKEHOUSE_BUNDLE_HOST_ROOT`, `LAKEHOUSE_BUNDLE_CONTAINER_ROOT`, `AIRFLOW_UID`, and the Docker socket group as applicable). Then run:

```bash
unset ROTATE_RUSTFS_WRITER_SECRET
./scripts/provision-identities.sh
```

This builds and runs the identity provisioner, reconciles identities and policies, and restarts Hive Metastore to apply its service credentials. Do not set `ROTATE_RUSTFS_WRITER_SECRET=true`; this change does not require rotating the writer credential. Confirm the command completes successfully and that it reports the `lakehouse-writer` policy as exact. If provisioning fails, stop and inspect sanitized service logs before retrying.

## 3. Refresh and verify Airflow

1. Start or update Airflow/Jenkins using the documented Compose procedure in `README.md`, with the expected Git Bundle configuration and host paths.
2. Wait for Airflow to fetch and parse the new Bundle revisions.
3. Run `./scripts/verify-airflow-environment-dags.sh`. Confirm production `main-init_environment` and UAT `uat-init_environment` are registered.
4. Resolve the existing `count_sample_rows.py` DAG processor import warning before treating the Airflow integration as clean.

## 4. Run the Spark workload only when its environment is enabled

The previously recorded Unit 2 design leaves UAT and production execution disabled until explicitly approved. Verify the selected environment's enablement and target paths before triggering any DAG. Do not enable or trigger UAT/production as part of this handoff without the appropriate operator decision.

For an approved enabled environment, trigger the matching `init_environment` DAG and verify:

- the run uses the immutable Bundle revision recorded by Airflow;
- the Spark driver logs the intended Kerberos writer principal without logging keytab or secret values;
- the job creates the configured Hive catalog namespace and sample table;
- the table's RustFS objects are written under the configured `storage_path` in bucket `lake`;
- a read/query of the sample table succeeds; and
- the per-run Spark containers are removed after success or failure.

If the workload returns S3 403, stop and check the runtime credential source and the effective writer policy before changing storage paths or rotating secrets.

## 5. Complete Jenkins and integrated verification

After obtaining the protected SCM URL/ref, run the trusted Jenkins Pipeline-from-SCM job and verify trusted-source admission, serialization, timeout failure behavior, retention, and workspace cleanup. The previous linter request returned HTTP 403; resolve Jenkins linter access or record an explicit accepted verification waiver. Rerun the approved integrated Unit 1–3 acceptance checks and record their outputs in the Build and Test summary.

## Stop and recovery conditions

- Stop if the provisioner reports policy drift, failed credential checks, or attempts to rotate the writer secret.
- Stop if the DAG runs under an unexpected Bundle revision or principal, if the S3 path is outside its configured prefix, or if data writes fail.
- No rollback procedure for deleting already-written sample objects is defined here. Preserve the data and ask the data owner before cleanup.
- Jenkins SCM inputs, trusted-build results, the import warning resolution, and integrated Unit 1–3 evidence are blockers to claiming complete verification.
