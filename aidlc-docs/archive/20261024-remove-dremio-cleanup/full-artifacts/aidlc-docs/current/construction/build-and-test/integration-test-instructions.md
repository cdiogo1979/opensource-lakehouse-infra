# Integration Test Instructions

## Status and preservation boundary

The live integration checks below were not run during this stage. They require starting or interacting with services that use existing persistent volumes. The TPCH workload writes Iceberg tables and creates run manifests, so run it only when that data change is intended. Do not use `docker compose down --volumes`.

## Compose model and image integration

Already passed:

1. `docker compose config --quiet`
2. Build all configured images with `docker compose --profile workload --profile identity-provisioning --profile jupyter-build build`
3. Verify relocated Compose paths and the absence of Dremio service entries.

## Live stack smoke test — not executed

When ready to exercise the local stack, inspect current containers first so you do not disrupt another running project:

```bash
docker compose ps
```

If the retained stack is intentionally to be started or refreshed, use:

```bash
./scripts/start.sh
docker compose ps
```

Expected services: KDC, PostgreSQL, Hive Metastore, RustFS, bucket initialization, Spark, and JupyterHub. Verify Hive Metastore and RustFS report healthy and JupyterHub/Spark endpoints are reachable on their configured loopback ports. Do not run `scripts/clean.sh` as part of this smoke test.

## TPCH ETL integration — data-writing; not executed

After confirming the existing table state and deciding that workload writes are acceptable:

```bash
./scripts/run-tpch-workload.sh
```

Expected behavior: the generator first removes existing `.tbl` files under ignored `.runtime/workload/tpch-data/` and regenerates them; Spark then authenticates as `write-service-account`, creates or validates the TPCH tables in `databaseA` and `databaseB`, writes to Hive/RustFS, and emits a redacted manifest under `.runtime/workload/results/`. A schema or row-count conflict should fail without replacing a table. Review the manifest and service logs without printing credentials.

This workload overwrites the generated TPCH input files and may update Hive metadata and RustFS objects. Preserve or back up anything in those locations that must not change before running it. It is not a read-only test.

## Removed-component runtime cleanup — not executed

The source configuration no longer defines Dremio, but removal of any pre-existing Dremio container/data volume, KDC principal, or credential/keytab has not been verified. `scripts/clean.sh` is a separately confirmation-gated operation and must only be run for the explicitly scoped Dremio-only runtime cleanup. It is outside this build check.
