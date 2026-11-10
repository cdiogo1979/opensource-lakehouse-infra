# Component Inventory

## Runtime and Infrastructure Components

- `object-store` — RustFS S3-compatible object storage.
- `create-bucket` — one-shot Python/boto3 bucket initializer.
- `dremio` — Dremio Community SQL engine.
- `spark` — interactive Spark/Iceberg runtime.
- `nessie` — Nessie catalog REST service.
- `nessie-db` — PostgreSQL persistence for Nessie.
- `tpch-generator` — TPCH source-data generator image.
- `tpch-loader` — one-shot Spark TPCH data loader.

## Supporting Components

- `scripts/` — Compose startup and cleanup scripts.
- `spark/` — Spark workloads and catalog properties.
- `tpch/` — data loading and table-registration scripts plus generated data.
- `sql/` — example query workload.

## Count

- **Compose services**: 8
- **Application/runtime services**: 3 (`dremio`, `spark`, `tpch-loader`)
- **Infrastructure/initialization services**: 5
- **Automated test packages**: None detected in the active project files.
