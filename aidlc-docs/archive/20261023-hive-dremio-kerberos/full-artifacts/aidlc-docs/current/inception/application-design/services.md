# Application Services and Orchestration

The PoC is composed as one Docker Compose project. The flows below identify logical one-shot/runtime services; they do not prescribe final image or entrypoint details.

## 1. Platform Bootstrap and Identity Provisioning

1. Compose starts PostgreSQL, KDC, RustFS, and the services required for initialization.
2. The KDC initialization operation creates service, test-user, admin, and writer principals/keytabs as local runtime artifacts.
3. Metastore schema initialization prepares PostgreSQL for Hive Metastore.
4. The identity/permission provisioner coordinates component-native setup: Dremio local users, Hive database grants, RustFS credentials/policies, and component-specific admin access.
5. RustFS bucket initialization creates the sample bucket/warehouse baseline.
6. Hive Metastore becomes ready after its database and service identity dependencies are available.

The provisioner is a setup coordinator. It does not make query-time authorization decisions, hold a central policy database, or replace component-native identity/authorization controls. The exact ordering among permissions and database creation must be resolved during Functional Design because some Hive grants may require databases to exist first.

## 2. Sample ETL and Dremio View Initialization

1. TPCH generator creates source data.
2. After Hive, RustFS, and writer credentials are ready, `tpch-loader` opens Spark as `write-service-account`.
3. The loader creates `databaseA` and `databaseB`, writes their Iceberg tables to RustFS, and registers table metadata with Hive Metastore.
4. The loader connects to Dremio over JDBC as `write-service-account` and creates matching Spaces named `databaseA` and `databaseB`, then a view for every Hive table in its corresponding Space.
5. The loader reports the effective identity and per-table outcomes. If the selected Dremio Community version blocks non-admin Space/view operations, preserve the failure as a feasibility result and request a reviewed design adjustment.

## 3. Dremio Query Path

1. Dremio connects to Hive Metastore using its configured Kerberos service identity and SASL.
2. A Dremio local account submits a query.
3. Dremio maps the local user to the intended Hive effective user and applies narrowly scoped proxy-user settings.
4. Hive authorization evaluates access to the database/table metadata; Dremio reads table data from RustFS using the configured source path.
5. The demonstration records effective user and allow/deny outcome. Dremio's support for these exact authorization and storage paths remains subject to compatibility verification.

## 4. Jupyter Spark Query Path

1. JupyterHub authenticates the local demo label through DummyAuthenticator and DockerSpawner starts a separate user container.
2. The user's own Kerberos keytab and RustFS credentials are mounted/injected for that session only.
3. Spark opens a Hive catalog session using that principal and reads Iceberg data from RustFS.
4. Hive/storage authorization evaluates the intended effective user. The scenario checks `user_a` against databaseA and databaseB, and `user_b` against both.

## 5. Administration and Cleanup

- `admin` uses component-specific administrator credentials/roles; Kerberos credentials are not repurposed as web/S3 credentials.
- Lifecycle scripts sequence Compose startup and cleanup. Cleanup must distinguish containers from persistent volumes and generated local credentials.
- Direct RustFS authorization is not a user-facing acceptance path, although RustFS credentials are required by Spark sessions and the writer ETL.
- Airflow/Jenkins job orchestration and credential injection are deferred.

## Service Boundaries

- Compose/lifecycle scripts own service startup order, not authorization policy.
- Identity provisioner owns one-shot coordination only.
- KDC, Hive, RustFS, and Dremio own their respective identity or permission mechanisms.
- TPCH loader owns the ETL operation and requested Dremio view creation.
- JupyterHub owns notebook lifecycle; Spark owns the query execution context within a notebook.
