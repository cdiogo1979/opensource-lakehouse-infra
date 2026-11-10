# Unit 2 Domain Entities — Airflow Bundle Runner

## Bundle identity

Stable logical identity for a maintained Git DAG Bundle and the configured Airflow environment mapping. It is distinct from the immutable revision resolved for a run.

## Bundle revision

Immutable source revision resolved by Airflow for one DAG run. It supplies the DAG, environment config, workload declarations, helpers, and workload files mounted read-only into the run's driver.

## Environment target

Named execution configuration selected by the bundle identity (`dev`, `uat`, or `prod`). It identifies a Hive catalog, namespace/table destination, and storage location. `dev` is locally configured. UAT/prod remain unavailable for Airflow execution until their endpoints and credentials are supplied.

## Hive catalog

One of `lakehouse_dev`, `lakehouse_uat`, or `lakehouse_prod`, registered in the Hive Metastore and addressed by supported clients. Each has its own warehouse prefix and contains `databaseA` and `databaseB`; the development workload additionally creates/overwrites its dedicated `test_database.test_airflow_generated_table` table.

## Namespace

Database-like container within a Hive catalog. The initial catalogs contain `databaseA` and `databaseB`. The dev sample workload's namespace is `test_database`.

## Storage prefix

Catalog-isolated RustFS object prefix. Catalog warehouse prefixes live under `s3a://lake/warehouse/`; the development sample table is managed under `s3a://lake/warehouse/lakehouse_dev/`. Prefix boundaries are used for writer/read authorization and to isolate catalog data.

## Principal

An authenticated identity with an explicit access policy:

- `write-service-account`: shared Kerberos/RustFS writer and catalog administrator for creating/writing across the three catalogs and their prefixes.
- `user_a` and `user_b`: equivalent normal reader identities with read-only access to both initial namespaces across all three catalogs and corresponding object data.

## DAG run

One Airflow execution instance with a selected environment, pinned bundle revision, validated workload graph, one ephemeral driver, one ephemeral worker, and a final success/failure result. Its containers, credentials, and caches are private to the run lifecycle.

## Workload declaration

Bundle-defined Spark task with its executable entry point and optional `runs_after` dependencies. The validated dependency graph determines when tasks may run and which tasks may run concurrently.

## Ephemeral Spark driver

Temporary Docker container created for one DAG run. It mounts the run's bundle read-only, obtains the writer TGT and RustFS access through protected files, submits to `spark://spark:7077`, and is removed after all run tasks settle.

## Ephemeral Spark worker

Temporary worker-only Docker container created once per DAG run and registered with the shared Spark Standalone master. It obtains its own writer TGT, uses its own private cache and read-only RustFS credentials, and is removed with the paired driver. It is lifecycle-dedicated but does not guarantee that the run's executors will be placed only on it.

## Writer credential set

Existing read-only keytab and RustFS credential file references for `write-service-account`, plus a private temporary Kerberos ticket cache. Credential values and ticket contents are not domain outputs and must not enter logs, bundle files, or task results.

## Workload result

Safe status for one declared workload, including success or a phase-specific failure. It contains diagnostics needed for Airflow observability but excludes secrets, keytab content, RustFS secret values, and ticket data.
