# Local Deployment and Cleanup Handoff

These steps are manual and are not executed by this handoff. The intended result is a running Hive, PostgreSQL, Kerberos, RustFS, Spark, and JupyterHub stack with only legacy Dremio-specific runtime state removed. Verification is incomplete until the live checks below are performed.

## Step 1 — Confirm the target project and preserve anything needed

- **Target:** This checkout at `/Users/carlosdiogo/code_repo/hive-dremio-rustfs` and the Compose project it renders.
- **Prerequisites:** Docker Engine and Compose v2. Confirm any Dremio data that must be retained has been backed up; removal of its volume is irreversible.
- **Execution:** From this project root, inspect `docker compose ps -a`. If needed, inspect container Compose labels with `docker inspect`. Confirm the legacy Dremio container and KDC belong to this checkout/project before proceeding.
- **Validation:** The Compose project name and working directory must match the legacy Dremio/KDC resources that `scripts/clean.sh` will inspect.
- **Failure handling:** If ownership is ambiguous or resources belong to another checkout/project, stop. Do not weaken the cleanup guards or delete by guessed name.

## Step 2 — Ensure the matching KDC is available

- **Target:** The existing KDC for this Compose project.
- **Prerequisites:** Step 1 is complete; its existing KDC volume and credentials are preserved.
- **Execution:** If the matching KDC container is stopped or absent, start only that service with `docker compose up -d kdc`. Do not start the full stack yet. If the KDC exists under a different project label or working directory, stop and resolve that mismatch first.
- **Validation:** `docker compose ps kdc` shows the matching KDC running and healthy.
- **Failure handling:** If it cannot become healthy, stop; the cleanup script intentionally refuses to delete the principal when it cannot verify KDC state.

## Step 3 — Remove only the approved Dremio runtime state

- **Target:** The uniquely identified Dremio container/data volume, `dremio@<KERBEROS_REALM>`, and exact Dremio-only password/keytab files.
- **Prerequisites:** Steps 1–2 are complete. Any Dremio data needed later has been backed up. The user has authorized this Dremio-only cleanup in the requirements.
- **Execution:** From this checkout, run `./scripts/clean.sh` and type the exact confirmation phrase requested by the script. This is manual and destructive.
- **Validation:** The script reports successful Dremio-only cleanup. It must preserve the KDC database, all non-Dremio credentials/principals, and all retained Compose volumes.
- **Failure handling:** If the script exits with an ambiguity/ownership/KDC error, stop. Do not manually substitute broad `docker compose down --volumes`, wildcard volume deletion, or a KDC reset. Resolve the exact target first.

## Step 4 — Start the retained platform

- **Target:** Retained services in this checkout.
- **Prerequisites:** Step 3 completed, or the user intentionally elects to defer runtime cleanup and has separately confirmed that startup is safe with existing resources.
- **Execution:** Run `./scripts/start.sh`. This builds/pulls and starts retained services; it is an automated project script invoked manually.
- **Validation:** `docker compose ps` shows retained services healthy. Confirm Hive Metastore and RustFS health checks pass and Spark/JupyterHub endpoints are reachable on configured loopback ports. Confirm no Dremio service/container was recreated by this checkout.
- **Failure handling:** Review service logs and stop at the failing dependency. `./scripts/stop.sh` stops this Compose project's services but preserves named volumes; do not use `down --volumes`.

## Step 5 — Optional retained identity provisioning

- **Target:** Kerberos, RustFS, and PostgreSQL identities used by the retained stack.
- **Prerequisites:** Only needed if the retained environment has not already been provisioned or if the user explicitly wants to re-verify provisioning.
- **Execution:** Run `./scripts/provision-identities.sh` from the project root. The script preserves existing credentials and does not rotate the RustFS writer secret unless explicitly configured.
- **Validation:** The command completes successfully and the `write-service-account` identity remains usable.
- **Failure handling:** Stop on provisioning errors and inspect logs without printing secret values. Do not reset the KDC or regenerate credentials wholesale.

## Step 6 — Optional read-only service and catalog smoke checks

- **Target:** Running Hive Metastore, Spark, and RustFS services.
- **Prerequisites:** Step 4 is complete; use an identity with existing read access.
- **Execution:** Inspect `docker compose ps` and service logs, then use the established notebook or Spark SQL session to list the retained `databaseA` and `databaseB` catalog objects and query a known sample table.
- **Validation:** The metastore is reachable and known retained tables can be read without Dremio.
- **Failure handling:** Record the failing service and identity; do not modify table data as part of this smoke check.

## Step 7 — Optional TPCH ETL verification (writes data)

- **Target:** `.runtime/workload/tpch-data/`, Hive metadata, RustFS objects, and `.runtime/workload/results/`.
- **Prerequisites:** Only proceed if overwriting generated TPCH input files and running/validating ETL writes are acceptable. Back up local input changes or data that must remain unchanged.
- **Execution:** Run `./scripts/run-tpch-workload.sh` manually.
- **Validation:** Review the redacted run manifest, expected table schemas/counts in `databaseA` and `databaseB`, and workload logs. Do not expose credentials.
- **Failure handling:** Stop on a schema/count conflict or authentication/storage error. The loader is designed to fail rather than replace conflicting tables. Do not delete Hive/RustFS state to make the check pass.

## Outstanding verification

Live stack health, catalog access, optional TPCH ETL, and removal of Dremio runtime state were not verified during Build and Test. No waiver has been accepted. Keep intent verification marked incomplete until required checks are completed or the user explicitly accepts a documented limitation.
