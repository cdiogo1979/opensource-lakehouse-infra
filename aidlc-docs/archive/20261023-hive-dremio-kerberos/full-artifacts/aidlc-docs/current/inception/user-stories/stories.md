# User Stories — Hive Catalog and Kerberos Authorization PoC

Stories are grouped by feature and use small, independently reviewable capabilities. Acceptance criteria are testable checklists, as approved in the story-generation plan. Requirement references point to `aidlc-docs/current/inception/requirements/requirements.md`.

## Catalog and Iceberg Data

### US-CAT-01 — Use Hive Metastore as the Iceberg catalog

**Story**: As a PoC operator, I want Spark-created Iceberg tables registered in a standalone Hive 3.x Metastore, so both Spark and Dremio can discover the same catalog entries while table data remains in RustFS.

**Acceptance criteria**

- [ ] Compose starts Hive Metastore with PostgreSQL metadata persistence and the selected compatible Hive 3.x release.
- [ ] Active Spark, TPCH loading/registration, and Jupyter configuration use Hive Metastore; Nessie services and active Nessie settings are removed.
- [ ] Spark can create and query Iceberg tables registered in Hive Metastore with data in RustFS.
- [ ] Dremio can connect to the Hive Metastore using the configured Kerberos service identity and query those tables.
- [ ] If the selected version combination cannot support this path, the incompatibility and smallest proposed adjustment are documented for approval.

**Traceability**: FR-01–05, FR-14; acceptance criteria 1–3.

### US-CAT-02 — Initialize repeatable sample databases and tables

**Story**: As the `write-service-account`, I want the sample Spark ETL to create and populate `databaseA`, `databaseB`, and their Iceberg tables, so the PoC data is produced with the same service identity intended for future ETL.

**Acceptance criteria**

- [ ] A documented startup sequence initializes the KDC and metastore schema, then runs the sample ETL as `write-service-account` to create both databases and sample tables.
- [ ] Both databases contain data queryable by Spark and Dremio.
- [ ] Spark authenticates to Hive with the `write-service-account` Kerberos principal and writes Iceberg data to RustFS using the service account's RustFS credentials.
- [ ] The service account has only the Hive and RustFS write permissions needed for `databaseA`, `databaseB`, and their warehouse paths; it does not use `admin` credentials.
- [ ] The effective identity in initialization output or logs is `write-service-account`.
- [ ] The initialization flow can be repeated on a clean local PoC deployment without requiring a manually configured Nessie catalog.

**Traceability**: FR-03–05, FR-14, FR-23; NFR-04, NFR-05, NFR-08; acceptance criteria 1–3, 12.

## Identity and Administration

### US-ID-01 — Create disposable Kerberos identities and credentials

**Story**: As a PoC operator, I want the local KDC initialization flow to create distinct test, service, and admin principals and generate their keytabs, so the demo has repeatable identities without committing credentials.

**Acceptance criteria**

- [ ] The disposable KDC creates distinct principals for `user_a`, `user_b`, `admin`, `write-service-account`, and the Hive service identity required by the selected design.
- [ ] The `write-service-account` has separate Kerberos and RustFS credentials for its sample Spark ETL; credentials are not reused from `admin`.
- [ ] Generated keytabs and passwords are local/runtime artifacts and are not tracked in source or included in image layers.
- [ ] Keytabs are mounted read-only where required and are not shared between test users.
- [ ] Example configuration contains placeholders rather than real credential material.

**Traceability**: FR-06–07, FR-19, FR-21, FR-23; NFR-01, NFR-08; acceptance criteria 7, 9–12.

### US-ID-02 — Administer in-scope platform components

**Story**: As the platform administrator, I want the `admin` identity mapped to the required administrator account or role in every in-scope component, so I can operate the local PoC without reusing one component's credentials everywhere.

**Acceptance criteria**

- [ ] `admin` has the intended administrative access for the KDC, Hive Metastore, PostgreSQL metastore backend, Dremio, Spark, JupyterHub, and RustFS.
- [ ] Where a component does not authenticate with Kerberos, its native administrator credential is provisioned separately.
- [ ] The Kerberos keytab is not reused as a web login or RustFS S3 secret.
- [ ] No Airflow/Jenkins administrator account or deployment change is included in this intent.

**Traceability**: FR-19–20; NFR-08; acceptance criteria 9 and 11.

### US-ID-03 — Propagate Dremio identity to Hive

**Story**: As a Dremio query user, I want Dremio to authenticate to Hive with its Kerberos service identity and map my local Dremio username to my Hive identity, so Hive authorization evaluates my effective user rather than a shared administrator.

**Acceptance criteria**

- [ ] Dremio's Hive source authenticates to Hive Metastore with Kerberos/SASL using the configured service identity.
- [ ] Dremio local usernames map explicitly to the intended Hive usernames.
- [ ] Hive/Hadoop proxy-user rules restrict impersonation to the required test users, groups, and hosts without wildcard access.
- [ ] Query output or logs make the effective Hive user visible for the authorization demonstration.

**Traceability**: FR-08–09, FR-11; NFR-03, NFR-05; acceptance criteria 3–6.

## Jupyter and Cross-Engine Authorization

### US-JH-01 — Use isolated Jupyter sessions for test users

**Story**: As a test user, I want a separate Jupyter session based on the existing `jupyter-platform/` setup, so I can run Spark with my own identity and storage credentials.

**Acceptance criteria**

- [ ] JupyterHub uses the selected Hub, DockerSpawner, and Spark single-user image baseline.
- [ ] DummyAuthenticator is retained only for this isolated PoC and the documentation states that usernames are labels, not verified identities.
- [ ] Each test user's Spark session uses that user's distinct Kerberos principal and read-only keytab mount.
- [ ] Spark in Jupyter uses per-user RustFS credentials/policies compatible with the selected database access rules.
- [ ] Direct RustFS access is not presented as an authorization acceptance scenario.

**Traceability**: FR-10–13, FR-17–18; NFR-02; acceptance criteria 7–8.

### US-AUTH-01 — Enforce the two database access profiles

**Story**: As the platform administrator, I want `databaseA` and `databaseB` to have the selected read permissions, so the PoC can show one restricted user and one broader user.

**Acceptance criteria**

- [ ] The authorization policy allows `user_a` to read `databaseA` only.
- [ ] The authorization policy allows `user_b` to read both `databaseA` and `databaseB`.
- [ ] The policy does not use broad proxy-user wildcards to achieve these outcomes.
- [ ] The implementation identifies which Hive/filesystem authorization mechanism enforces the outcome for the selected service versions.

**Traceability**: FR-14–15; NFR-03; acceptance criteria 4–6.

### US-AUTH-02 — Verify Dremio allow and deny results

**Story**: As a Dremio query user, I want my access to both databases to match my assigned profile, so I can query permitted data and receive a clear denial for restricted data.

**Acceptance criteria**

- [ ] `user_a` can query `databaseA` and is denied when querying `databaseB` through Dremio.
- [ ] `user_b` can query both databases through Dremio.
- [ ] The effective username and allow/deny result are observable in command output or logs.
- [ ] Any inability of the selected Dremio/Hive/RustFS combination to enforce this behavior is reported as a feasibility blocker, not counted as a passing scenario.

**Traceability**: FR-09, FR-15–16; NFR-05; acceptance criteria 3–6.

### US-AUTH-03 — Verify Spark allow and deny results in Jupyter

**Story**: As a notebook user, I want Spark queries to enforce the same database access profile as Dremio, so using the notebook path does not bypass authorization.

**Acceptance criteria**

- [ ] `user_a` can query `databaseA` and is denied when querying `databaseB` from their Jupyter Spark session.
- [ ] `user_b` can query both databases from their Jupyter Spark session.
- [ ] The session uses the matching Kerberos principal and RustFS credentials, and output or logs show the effective identity and outcome.
- [ ] If storage-based authorization cannot enforce the expected results over RustFS for the selected versions, the gap and smallest architecture adjustment are returned for approval.

**Traceability**: FR-10–11, FR-15–18; NFR-03, NFR-05; acceptance criteria 2, 4–7.

## Dremio JDBC Writer

### US-JDBC-01 — Create an object in a Dremio Space

**Story**: As the `write-service-account`, I want to connect to Dremio over JDBC and create an object, at minimum a table, in a designated existing Space, so a future Airflow-triggered Spark workflow can use this identity without making it a platform administrator.

**Acceptance criteria**

- [ ] The `write-service-account` Kerberos principal and corresponding Dremio local user are created.
- [ ] A JDBC connection using the Dremio user's credentials can create at least a table in the designated existing Space.
- [ ] The writer is not granted platform-administrator privileges.
- [ ] The exact Dremio Community version's ability to grant or provide this non-admin Space write capability is verified before implementation is considered complete.
- [ ] If Community cannot provide the required capability, the story is marked blocked and an alternative is presented for approval; administrator privileges are not used as a workaround.
- [ ] Airflow/Jenkins changes, job launch, and Spark credential injection remain deferred.

**Traceability**: FR-21–23; NFR-08; acceptance criteria 10–11.

## Operator Documentation

### US-DOC-01 — Set up, demonstrate, and clean up the PoC

**Story**: As a PoC operator, I want setup, demonstration, and cleanup instructions, so another operator can reproduce the identity and authorization scenarios safely.

**Acceptance criteria**

- [ ] Documentation gives the startup and cleanup sequence, local credential lifecycle, and allow/deny commands for Dremio and Jupyter Spark.
- [ ] Documentation explains DummyAuthenticator's development-only limitation and the non-production scope.
- [ ] Documentation records version compatibility and authorization feasibility results, including any unresolved Dremio Community Space-write blocker.
- [ ] Documentation states that Airflow/Jenkins integration is deferred and that no direct RustFS authorization test is included.

**Traceability**: FR-05, FR-13, FR-16–17, FR-21–23; NFR-01–02, NFR-04–05; acceptance criterion 8.

## Story Quality and Scope Notes

- Stories are organized by feature, use concise checklist acceptance criteria, and describe one capability or access outcome apiece.
- Each story is independently reviewable and testable at its boundary; environment setup dependencies are captured in traceability and acceptance criteria rather than hidden.
- `write-service-account` is an actor, not a human persona. Future Airflow/Jenkins behavior is explicitly excluded from current acceptance.
- Cross-engine authorization and non-admin Dremio Community Space writes remain feasibility-dependent; the stories do not presume these behaviors are supported.
