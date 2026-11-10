# StarRocks Integration — Personas

These personas represent the native StarRocks SQL identities and the operator roles in the approved local PoC requirements. They do not imply that StarRocks SQL authentication is Kerberos authentication; StarRocks uses a service identity for HMS/RustFS access while applying SQL permissions to the connected account.

## Analyst — `user_a`

- **Role**: Analyst with access to the curated `databaseA` dataset.
- **Needs**: Query permitted Iceberg tables through StarRocks SQL.
- **Access boundary**: Read `databaseA`; be denied access to `databaseB` through StarRocks.
- **Success**: Queries work on allowed tables, while the denied database cannot be accessed.

## Analyst — `user_b`

- **Role**: Analyst who needs visibility across the two sample databases.
- **Needs**: Query Iceberg tables in `databaseA` and `databaseB` through StarRocks SQL.
- **Access boundary**: Read both databases; no write permission.
- **Success**: Queries work in both databases and write attempts are denied.

## ETL Writer Service Account — `write-service-account`

- **Role**: Non-human account used by data pipelines and future orchestration.
- **Needs**: Read and write Iceberg tables in both sample databases through StarRocks SQL.
- **Access boundary**: Access is limited to the two approved databases and the StarRocks storage service identity is separately scoped to the Iceberg warehouse prefix.
- **Success**: Can write Iceberg data and read the committed result; cannot administer StarRocks users or configuration.
- **SQL name**: `write_service_account` if the StarRocks identifier grammar requires replacing hyphens; the Kerberos/RustFS identity remains `write-service-account`.

## StarRocks Administrator — `admin`

- **Role**: Platform administrator responsible for StarRocks configuration and user/role management.
- **Needs**: Full administrative access within StarRocks.
- **Boundary**: StarRocks administrator status does not automatically grant RustFS, PostgreSQL, KDC, or host-level administrator privileges.
- **Success**: Can inspect and manage StarRocks catalogs, users, roles, and queries.

## Platform Operator

- **Role**: Developer/operator of the local Docker Compose PoC.
- **Needs**: Start, inspect, and recreate the StarRocks service without losing its persistent state or exposing credentials.
- **Success**: Can validate service readiness, access loopback-bound endpoints, and follow documented resource and startup guidance.
