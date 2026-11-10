# Code Generation Summary — Unit 1

## Modified

- `docker-compose.yml`, `.env`, and `.env.example` — removed Dremio-only service, profile, ports, volume, secret, image tag, and local environment settings.
- `infra/hive/core-site.xml.in`, `infra/kerberos/entrypoint.sh`, `infra/kerberos/healthcheck.sh`, and `infra/identity-provisioner/provision-kerberos-identities.sh` — removed Dremio proxy/identity provisioning while retaining Hive and workload identities.
- `infra/tpch-loader/Dockerfile`, `infra/tpch-loader/run-workload.sh`, `infra/tpch-loader/load_tpch.py`, and `scripts/run-tpch-workload.sh` — removed the Dremio JDBC phase and kept the Spark/Hive/RustFS ETL and its run manifest.
- `scripts/bootstrap-local.sh`, `scripts/provision-identities.sh`, `scripts/start.sh`, and `scripts/clean.sh` — removed Dremio startup/password setup and added an explicit, label-validated Dremio-only runtime cleanup operation.
- `README.md` and the two approved canonical knowledge documents — updated to describe the retained local stack and operations.

## Removed

- `infra/dremio/dremio.conf`
- `infra/dremio/hive3.d/conf/core-site.xml`
- `infra/tpch-loader/dremio_jdbc.py`
- `infra/tpch-loader/run-jdbc.sh`
- `sql/dremio-authz-matrix.sql`

## Layout cleanup

- Moved the Spark service configuration to `infra/spark/`, the TPCH loader into `infra/tpch-loader/`, and the TPCH generator into `infra/tpch-generator/`; Compose mounts/build contexts now use those paths.
- Removed the unused standalone Iceberg seed script and stale Dremio SQL examples.
- Removed root `tpch/data/*.tbl` duplicates after confirming every file matched the retained ignored `.runtime/workload/tpch-data/*.tbl` copy byte-for-byte. Runtime workload inputs remain intact.

## Runtime State

No Docker container/volume, KDC principal, or `.runtime` credential/keytab has been removed during Code Generation. The new `scripts/clean.sh` is confirmation-gated and intended for the one-time runtime cleanup after this code review.

## Verification

- Static source review found no Dremio operational dependency in the retained Compose, Kerberos/Hive, TPCH workload, or identity/startup scripts.
- Remaining Dremio source mentions are intentionally limited to the migration cleanup script and its README guidance.
- No tests or builds were run in this stage.
