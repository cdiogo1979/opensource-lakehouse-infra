# Technology Stack

## Languages and Tools

- **Python** — boto3 bucket initialization and Spark/TPCH workload scripts.
- **Shell** — lifecycle and TPCH generator scripts.
- **Docker Compose** — local service orchestration.
- **SQL** — Spark and Dremio query workloads.

## Runtime Images

- Dremio Community `26.0.5`.
- RustFS `1.0.0`.
- Spark `3.5.5` with Iceberg `1.8.1` via `tabulario/spark-iceberg:3.5.5_1.8.1`.
- Nessie `0.109.0`.
- PostgreSQL `17`.
- Python `3.12-alpine` for bucket creation.

## Storage and Networking

- RustFS S3-compatible endpoint, path-style access enabled for Spark.
- Iceberg warehouse root `s3a://lake/warehouse`.
- Named Docker volumes for RustFS, Dremio, and Nessie database state.
- Internal Compose bridge network `iceberg-poc-net`.

## Identity and Security (Observed)

- Static RustFS credentials are defined in `.env` and repeated as literal Spark properties.
- Nessie database credentials are literal Compose environment values.
- No Kerberos KDC, realm, principals, keytabs, krb5.conf, or impersonation settings are present.

## Testing

- No dedicated unit or integration test harness is present in the active POC tree.
- `spark/test-nessie.py` is a manual runtime helper, not a conventional automated test suite.
