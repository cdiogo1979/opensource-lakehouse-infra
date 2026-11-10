# User Personas

## Persona 1 — Platform Operator

- **Role**: Runs and supports the local lakehouse platform and Airflow workflows.
- **Goals**: Start a DAG run against the intended bundle environment, see whether it succeeded, and have temporary run resources cleaned up.
- **Responsibilities**: Operate Airflow and the Compose services, select an allowed bundle environment, and investigate run failures using Airflow status and logs.
- **Relevant constraints**: Development targets the local lakehouse. UAT and production remain unconfigured placeholders. Spark workers use the shared writer service identity, so access is not individually attributed to the DAG author at the storage layer.
- **Stories**: US-01, US-02, US-04, US-06.

## Persona 2 — ETL Workload Author

- **Role**: Maintains DAG bundle workloads that read and write lakehouse data.
- **Goals**: Make a workload available as an immutable bundle revision and write Hive/Iceberg data files to RustFS through the supported Spark workflow.
- **Responsibilities**: Maintain DAG and workload code in the configured Git repository, respect the bundle's run-pinned read-only contract, and use the provided Spark runtime rather than embedding credentials.
- **Relevant constraints**: Workloads execute through an ephemeral Spark driver that submits to the existing Spark cluster. The existing Kerberos and RustFS writer identity is shared by driver and workers; secrets and keytabs must remain outside source and bundle content.
- **Stories**: US-01, US-03.

## Persona Boundaries

These personas describe workflow responsibilities, not new authentication identities. The approved requirements retain the existing writer service account and do not create per-author Spark identities. Jenkins validation is represented as a capability used by maintainers in US-05, rather than introducing a third persona outside the selected scope.
