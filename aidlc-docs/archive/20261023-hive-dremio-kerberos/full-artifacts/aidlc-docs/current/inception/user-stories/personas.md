# Personas — Hive Catalog and Kerberos Authorization PoC

These are test personas for the isolated development PoC, not verified production identities. JupyterHub's DummyAuthenticator does not prove that a person owns the supplied username.

## Platform Administrator

- **Identity**: `admin` with component-native administrator accounts and a Kerberos principal where required.
- **Goals**: Start and initialize the PoC, administer in-scope services, create the test data and authorization setup, and inspect results.
- **Needs**: Repeatable setup and cleanup instructions, separate component credentials, and clear evidence of effective identities and allow/deny outcomes.
- **Boundaries**: Administrative access is limited to this local PoC. Airflow/Jenkins is not part of the current deployment scope.
- **Related stories**: US-CAT-01, US-CAT-02, US-ID-01, US-ID-02, US-AUTH-01, US-DOC-01.

## Restricted Data User (`user_a`)

- **Identity**: Dremio local account and corresponding Hive/Spark Kerberos test identity; JupyterHub username is a test label.
- **Goals**: Query permitted Iceberg data from Dremio and Spark in a Jupyter session.
- **Access profile**: Read `databaseA`; receive a clear denial for `databaseB`.
- **Needs**: A distinct keytab and per-user RustFS credentials in the notebook session, with the effective identity visible in the demo.
- **Boundaries**: Cannot use the test setup to access `databaseB`; direct RustFS access is not an acceptance scenario.
- **Related stories**: US-ID-01, US-ID-03, US-JH-01, US-AUTH-01, US-AUTH-02, US-AUTH-03, US-DOC-01.

## Broader Data User (`user_b`)

- **Identity**: Dremio local account and corresponding Hive/Spark Kerberos test identity; JupyterHub username is a test label.
- **Goals**: Query the full sample dataset from Dremio and Spark in a Jupyter session.
- **Access profile**: Read both `databaseA` and `databaseB`.
- **Needs**: A distinct keytab and per-user RustFS credentials in the notebook session, with the effective identity visible in the demo.
- **Boundaries**: Remains a test user, not a platform administrator.
- **Related stories**: US-ID-01, US-ID-03, US-JH-01, US-AUTH-01, US-AUTH-02, US-AUTH-03, US-DOC-01.

## Non-Human Actor: `write-service-account`

This service identity is represented as an actor in US-CAT-02 and US-JDBC-01 rather than as a human persona. It runs the sample Spark ETL to create/populate both Hive databases and write their Iceberg data to RustFS, and it must create an object in a designated existing Dremio Space over JDBC without platform-admin privileges. It uses its own Kerberos and RustFS credentials. Future Airflow/Jenkins job integration is deferred. A human owner/operator is not specified in the approved requirements and is therefore not invented here.
