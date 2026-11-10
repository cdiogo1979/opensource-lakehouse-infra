# Unit 2 Business Rules — Airflow Bundle Runner

## Bundle and environment rules

1. A DAG run uses exactly one resolved bundle revision. Every file it executes or reads as configuration comes from that revision.
2. A bundle is mounted read-only in the Spark driver. Runtime credentials, ticket caches, and mutable output never live in the bundle checkout.
3. Environment selection is explicit and validated before driver creation. Only the configured `dev` target may use this local Compose lakehouse.
4. UAT and production may have Hive catalog metadata initialized locally as requested, but their Airflow endpoints remain unconfigured. A selected unconfigured environment fails closed and cannot use dev resources.

## Workload and run rules

5. One DAG run creates exactly one ephemeral Spark driver and one ephemeral Spark worker. Keep the existing long-lived worker for notebooks and other clients.
6. Admit at most two DAG runs concurrently. Additional runs wait in the Airflow queue. Each admitted run receives its own driver, worker, credential mounts, and private ticket caches.
7. The per-run worker registers with the shared Spark Standalone master and is dedicated to that run's lifecycle, but executors are not exclusively assigned to it. Spark may schedule a run's executors on any registered worker.
8. Independent workloads may run in parallel only when their dependency graph permits it. A workload starts only after every `runs_after` dependency succeeds. Invalid or cyclic dependency graphs fail validation before either run container is created.
9. All Spark applications submit to `spark://spark:7077`; local-only execution is not an acceptable fallback.
10. The existing writer principal and matching RustFS credentials are used. Keytab and secret files are read-only to the driver and worker; each has a private run-scoped TGT cache and validates its own TGT before it becomes ready.
11. The workload identity's approved grants are broad across the three Hive catalogs and associated object prefixes. A DAG author does not receive individual storage-level authorization through this shared writer identity.
12. The sample workload owns only `lakehouse_dev.test_database.test_airflow_generated_table` and its dev storage location. It may create or replace that sample table, but it cannot modify TPCH tables or unrelated data.

## Catalog and authorization rules

11. Hive catalog initialization creates `lakehouse_dev`, `lakehouse_uat`, and `lakehouse_prod`, each with `databaseA` and `databaseB`.
12. Each catalog has an isolated RustFS warehouse prefix under `s3a://lake/warehouse/`; no catalog can write into another catalog's prefix unless an explicit shared operation is later approved.
13. `write-service-account` has administrative catalog operations needed to create namespaces/tables and write data in all three catalogs and their storage prefixes.
14. `user_a` and `user_b` have equivalent read-only rights in both namespaces across all three catalogs and read-only access to the corresponding object data.
15. StarRocks is query-only for normal readers. Do not grant reader write privileges there. Keep any platform/bootstrap administrator separate from these normal reader permissions.
16. Multi-catalog permissions must be enforced consistently by each participating engine and storage access path. If supported Hive, Spark, StarRocks, or RustFS authorization cannot enforce the specified policy, do not report the access model as implemented.

## Failure and cleanup rules

19. Invalid bundle identity, unavailable environment, malformed configuration, invalid workload declarations, or invalid dependencies fail before driver or worker creation.
20. Driver/worker creation, worker registration, Kerberos acquisition, Spark submission, workload execution, and cleanup failures are reported distinctly enough to identify the failing phase without returning credential values or ticket contents.
21. Cleanup of both run containers is attempted after every started run, including task failures and cancellation. An already absent container is treated as cleaned up.
22. Cleanup failure does not erase the original workload failure; report both when applicable.
23. Run cleanup never deletes or modifies persistent Hive metadata, RustFS warehouse data, the bundle revision, the long-lived Spark service, or existing named volumes.
24. Retries use the same run-pinned bundle revision for an existing DAG run. A newly triggered run resolves its own pinned revision under the configured Airflow Bundle behavior.

## Design delta to approved requirements

The accepted clarifications change the prior single `iceberg` catalog assumption, the previously distinct reader grants, and the shared-worker-only Airflow topology. Before implementation, update the applicable requirements, story acceptance criteria, and application/service design to reflect three Hive catalogs, equivalent read-only access for `user_a`/`user_b`, writer/admin access across all catalogs, local catalog initialization while keeping UAT/prod Airflow targets unavailable, and one ephemeral driver/worker pair per DAG run with shared Spark scheduling. Preserve the fail-closed environment rule and validate engine support before claiming this change complete.
