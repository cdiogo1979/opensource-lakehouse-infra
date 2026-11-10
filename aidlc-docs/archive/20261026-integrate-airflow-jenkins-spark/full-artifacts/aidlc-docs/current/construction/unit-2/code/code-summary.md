# Unit 2 Code Summary — Airflow Bundle Runner

## Generated and Adapted Files

- `dags/dag_factory.py` — validates workload declarations/dependencies, caps active DAG runs at two, creates one run-labeled driver/worker pair, waits for readiness, submits jobs to `spark://spark:7077`, and cleans only that run's containers.
- `dags/dag_defaults.py`, `dags/init_environment.py`, `dags/.airflowignore` — maintained Bundle defaults and manual-only sample DAG.
- `configs/dev.yml`, `configs/uat.yml`, `configs/prod.yml` — catalog-specific dev paths; UAT/prod are explicitly disabled.
- `notebooks/common/{__init__.py,cli.py,config_loader.py,job_runtime.py}` — shared configuration validation and Spark job startup.
- `notebooks/workload/{init_environment.py,count_sample_rows.py,jupyter_helper.py}` — sample table creation/read and notebook startup support.
- `infra/spark/entrypoint.sh` — retained the default long-lived `service` role and added ephemeral `driver` and `worker` roles with separate private Kerberos/AWS credential state.
- `README.md` — documented the Bundle layout, dev target, run pair lifecycle, host path mappings, and verification limits.

## Traceability

- **Per-run isolation and immutable source**: each run's driver receives a read-only bind of its exact resolved Bundle checkout; stable run labels scope discovery/removal.
- **Writer identity**: both ephemeral roles read only the existing writer keytab and RustFS writer credential files, check restrictive file modes, create an independent private TGT/cache, and keep derived credentials in tmpfs.
- **Approved sample target**: the dev workload targets `lakehouse_dev.test_database.test_airflow_generated_table` and its catalog-specific RustFS prefix using the writer runtime identity.
- **Fail-closed environments**: UAT/prod configs have `enabled: false`; config validation rejects them before creating containers.
- **Readiness and concurrency**: the DAG is limited to two active runs, polls pair readiness every five seconds, and uses a five-minute deadline measured from initial pair creation.
- **Cleanup**: run-labeled cleanup requests worker decommission, stops the driver, checks master worker occupancy where observable, and removes the worker by the shared 60-second deadline. Unknown occupancy is treated as not drained and results in `worker_drain_timeout`.

## Boundaries and Verification Gaps

- No `docker-compose.yml`, Jenkins pipeline, Dockerfile, runtime credential, Hive schema, RustFS object, or persistent volume was changed.
- No tests were added or run, and the derived image was not built. The long-lived service mode was preserved by code inspection only.
- Unit 3 must provide the scheduler's Docker socket, project root, Bundle host/container root mappings, writer credential paths, and network access. Until then, this runner cannot be launched by the integrated Airflow stack.
- The worker readiness check matches the worker container IP/hostname against Spark master JSON. The drain observer expects a matching worker `host` and `coresused`/`coresUsed` field. Neither Spark JSON contract has been exercised here; an unknown value deliberately waits to the 60-second deadline and reports timeout.
- The pinned Spark decommission command's effect on new scheduling, executor drain, worker exit, and cross-run impact remains unverified. Spark Standalone may schedule the workload on any registered worker.
- Spark catalog and RustFS authorization across all three catalogs, sample write/query, actual metastore writer identity, secret-safe logs, Bundle mapping, Docker path visibility, failure cleanup, and readiness/cleanup timing are integrated Build and Test gates.
- No throughput, capacity, or production-readiness claim is made.
