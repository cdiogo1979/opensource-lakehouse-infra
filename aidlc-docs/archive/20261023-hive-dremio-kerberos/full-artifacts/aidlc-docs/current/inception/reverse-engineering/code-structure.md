# Code Structure

## Build System

- **Type**: Docker Compose; no application build/test system detected.
- **Configuration**: `docker-compose.yml`, `.env`, `spark/spark-defaults.conf`.
- **Startup and cleanup**: `scripts/start.sh`, `scripts/clean.sh`.

## Existing Files Inventory

- `docker-compose.yml` — service definitions, dependencies, volumes, network and health checks.
- `.env` — local ports and RustFS credentials.
- `README.md` — operator setup and Dremio source instructions; currently describes a Nessie-free approach and is inconsistent with the active Compose file.
- `spark/spark-defaults.conf` — Iceberg Spark extensions, Nessie catalog, and RustFS credentials/configuration.
- `spark/seed.py` — Spark seed workload.
- `spark/test-nessie.py` — catalog test helper.
- `tpch/load_tpch.py` — loads TPCH files into Iceberg using the `nessie` catalog.
- `tpch/register_missing.py` — registers missing TPCH Iceberg tables through Nessie procedures.
- `tpch-generator/Dockerfile`, `tpch-generator/generate.sh` — build and run TPCH data generation.
- `sql/queries.sql` — sample Dremio SQL.
- `scripts/start.sh`, `scripts/clean.sh` — Compose lifecycle helpers.

## Design Patterns

- Infrastructure is declared in Compose.
- Spark catalog settings are mounted as a properties file into Spark images.
- One-shot services use `depends_on` completion/health conditions.
- Credentials are supplied from `.env` into service environment variables, with some credentials also hard-coded in Spark properties.

## Critical Dependencies

- Dremio Community image `dremio/dremio-oss:26.0.5`.
- RustFS image `rustfs/rustfs:1.0.0`.
- Spark/Iceberg image `tabulario/spark-iceberg:3.5.5_1.8.1`.
- Nessie image `ghcr.io/projectnessie/nessie:0.109.0`.
- PostgreSQL image `postgres:17`.
- TPCH generator downloads upstream `tpch-dbgen` source during image build.
