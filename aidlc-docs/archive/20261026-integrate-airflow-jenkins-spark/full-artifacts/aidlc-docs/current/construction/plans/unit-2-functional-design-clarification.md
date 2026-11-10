# Unit 2 Functional Design — Clarification

Your answer proposes three Hive catalogs (`lakehouse_dev`, `lakehouse_uat`, and `lakehouse_prod`), each containing `databaseA` and `databaseB`, broadens the writer identity to all catalogs and databases, and gives `user_a` and `user_b` the same rights.

These decisions differ from the approved baseline and checked-in configuration: Spark currently defines one Hive-backed Iceberg catalog named `iceberg`; the sample namespaces are `databaseA` and `databaseB`; and the existing StarRocks policy gives `user_a` and `user_b` different read access. The approved workflow also keeps UAT and production unavailable until configured. Please answer each question so the design can be updated consistently.

## Question 1 — Catalog topology

Which topology should this integration implement?

A) Keep one Hive Metastore-backed Iceberg catalog named `iceberg`, with `databaseA` and `databaseB` namespaces. Treat dev/uat/prod as Airflow environment labels/configurations; only dev targets this local stack. (Matches the current stack and approved environment boundary.)

B) Create three real Hive catalogs named `lakehouse_dev`, `lakehouse_uat`, and `lakehouse_prod`, each containing `databaseA` and `databaseB`. This changes the Hive/Spark architecture and requires defining how UAT/prod catalogs are provisioned without connecting them to this local stack.

C) Other; specify the catalog names, Hive namespaces, and which environments are provisioned in this local stack.

**[Answer]:** B

## Question 2 — Principal permissions and scope

Please specify the intended permissions and where they apply. The current baseline distinguishes users: `user_a` is restricted to databaseA while `user_b` can read databaseA and databaseB in StarRocks. “Same rights” does not identify whether both should be readers, writers, or administrators, or whether the policy is for Hive/Spark, RustFS, StarRocks, or all of them. The writer identity is currently scoped to the approved workload's target rather than implicitly granted access to every catalog/database.

For each principal, state the intended permissions and component scope:

- `write-service-account`: write (and any required read/create/drop permissions) in which catalogs/namespaces and object-store prefixes? Should this change apply to Hive/Spark and RustFS, StarRocks, or both?
- `user_a` and `user_b`: should they have identical read-only access to both namespaces, identical read/write access, or another identical permission set? Apply this to Hive/Spark, StarRocks, or both?
- Should the existing StarRocks access distinction be removed as part of this intent?

**[Answer]:** write-service-account is the main service account is can act as admin/write access creating the objects is catalog and filesystem. user_a and user_b represent normal read users. For making it easier they should have the same access on the 3 catalogs. For now , starrocks will work only as query engine , so only read access to catalog and fs is needed

## Question 3 — Development workload destination

For the dev Airflow bundle's sample workload, provide its exact catalog, namespace, and RustFS storage prefix. Should it create/overwrite only its dedicated synthetic sample table under a separate prefix, preserving the TPCH tables in `databaseA`/`databaseB`?

**[Answer]:** lakehouse_dev.test_database.test_airflow_generated_table

## Resolution

- Provision Hive catalogs `lakehouse_dev`, `lakehouse_uat`, and `lakehouse_prod`, each with `databaseA` and `databaseB` namespaces. Airflow bundle environment selection remains fail-closed: only `dev` is configured to run locally until UAT/prod endpoints are supplied.
- `write-service-account` is the service writer/admin identity with catalog/object creation and write access across all three catalogs and their storage locations.
- `user_a` and `user_b` are equivalent normal reader identities with read-only access to both namespaces in all three catalogs and read-only access to the associated object data. StarRocks remains a query engine and exposes no write workflow to these users.
- The dev workload targets `lakehouse_dev.test_database.test_airflow_generated_table`. Its catalog warehouse is assigned a dedicated dev prefix under `s3a://lake/warehouse/lakehouse_dev/`; the table location is managed below that warehouse. This keeps workload data separate from the existing TPCH databaseA/databaseB locations.
- The current Spark configuration and StarRocks external-catalog setup are single-catalog configurations. Support for all three Hive 3 catalogs through each engine is an explicit infrastructure/code-generation compatibility check; this functional design does not claim that the current runtime already supports it.

## Gate

After answering, reply `done`. The functional design plan and its architecture assumptions will then be updated before generating Unit 2 design artifacts.
