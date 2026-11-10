# User Personas — Central Identity and Environment Access

## Platform Identity Administrator

Manages human accounts, role-group membership, service identities, and identity lifecycle in FreeIPA. Needs group changes to flow to the platform’s enforcement points and needs a clear way to verify grants and revocations.

## Developer

Uses JupyterHub and Spark for development. Can read production, development, and UAT data, but can write only to the development environment.

## Analyst

Uses approved interactive tools to analyze production data. Can read production data and cannot write to any environment.

## ETL Workload Owner

Maintains Airflow-triggered Spark workloads. Workloads use the non-interactive `write-service-account`, which can read and write all three environments. The owner must keep service credentials out of notebooks, bundles, and logs.

## Lakehouse Operator

Operates FreeIPA, RustFS, Hive Metastore, Spark, JupyterHub, Ranger/StarRocks, and the provisioning workflow. Needs safe, repeatable provisioning and evidence that the intended access boundaries are enforced.

## Platform Administrator

Uses the existing `admin` identity for platform administration. This persona is kept separate from ordinary developer and analyst data access.
