# Build and Test Summary — Unit 2 Identity Provisioning

## Status

**COMPLETE — all Unit 2 build-and-test gates passed.** The existing local Compose environment was retained; no persistent volumes were reset. The stack now uses a native arm64 Hive 3.1.3 Metastore runtime, the approved one-shot provisioner completed and reran idempotently, RustFS authorization scopes passed, the PostgreSQL role migration completed, and Hive is healthy with its named RustFS service identity.

## Results

Representative commands used:

```sh
./scripts/bootstrap-local.sh
docker compose config --quiet
docker compose build kdc identity-provisioner create-bucket hive-schema-init hive-metastore
./scripts/provision-identities.sh
docker compose --profile identity-provisioning run --rm -e VERIFY_RUSTFS_AUTHORIZATION=true identity-provisioner
docker compose ps
```

The Spark namespace check ran as a Kerberos-authenticated local Spark SQL session using a pre-authenticated ticket cache; temporary ticket/keytab files were removed afterward. Provisioner output was redacted and did not print credential values.

### Passed

- `./scripts/bootstrap-local.sh` and `docker compose config --quiet` completed. Existing secret values were preserved and not displayed. Local image builds completed, including the native-arm64 Hive 3.1.3 image.
- Existing KDC and PostgreSQL volumes were preserved. The provisioner keytab was added without replacing the Hive service identity/keytab. Kerberos principals/keytabs for `admin`, `write-service-account`, `user_a`, and `user_b` were provisioned and authenticated; the existing Hive service principal remained usable.
- Hive schema initialization inspected PostgreSQL directly and confirmed the existing schema version is 3.1.0 without running schema DDL. Hive Metastore started natively on arm64 and passed its Thrift health check. Hive was restarted after switching to its named RustFS key and remained healthy.
- Dremio local `admin` and `write-service-account` accounts were manually created by the user. Non-mutating API login checks passed for both. Dremio account creation is a manual prerequisite and is outside the provisioner's API work.
- RustFS policies and named identities (`admin`, `write-service-account`, `hive-metastore`, `user_a`, `user_b`) were created. S3 authentication checks passed for the named identities. The provisioner's authorization probes confirmed the writer can write to the approved database prefixes, `user_a` can read only databaseA and cannot write databaseB, and `user_b` can read both. Temporary probe objects were removed.
- A second provisioner run reported existing identities/policies/roles without rotating credentials or duplicating grants.
- PostgreSQL role checks passed: named `admin` is a login superuser; service `hive` is a login without superuser privileges; the immutable bootstrap superuser is retained as `postgres_bootstrap` with login disabled. Metastore schema version remains 3.1.0 and existing database metadata remains present. No schema or volume reset occurred.
- Hive's generated configuration uses the named `hive-metastore` RustFS access key and not the RustFS root key. Hive Metastore remained healthy after restart.
- Spark authenticated to Hive with a Kerberos ticket cache and successfully ran `SHOW NAMESPACES IN iceberg`. This validates the namespace interaction in local mode; Spark standalone `local[1]` does not perform keytab login through its `--principal/--keytab` options, so the check used a pre-authenticated ticket cache.
- Final `docker compose ps` showed Dremio, Hive Metastore, KDC, PostgreSQL, RustFS, and Spark running; Hive, KDC, and PostgreSQL health checks were healthy.

### Limitations and deferred scope

- Spark standalone/local mode was verified with a ticket cache. Long-running keytab acquisition/renewal is a deployment-mode concern and was not demonstrated here.
- Dremio JDBC creation of objects in Spaces, Dremio Hive source behavior, end-user impersonation, and the cross-engine databaseA/databaseB access demonstration belong to later units and are not asserted as passed by Unit 2. Airflow/Jenkins integration and sample ETL/data creation are also deferred.
- Spark emits Hive configuration warnings for properties it does not recognize. The namespace smoke check succeeds, and independent read-only PostgreSQL inspection confirms the Hive schema remains 3.1.0; no schema repair or initialization was performed.

## Safety

- No Docker volume was deleted or reset. Existing credentials were preserved; generated credentials remained in protected local files and were not printed.
- Temporary ticket-cache/keytab copies and RustFS probe objects were removed after checks.
- No sample databases or tables were created in this unit.

## Completion

Unit 2 Build and Test is complete under its approved plan. Proceed to the next planned construction unit; retain Dremio JDBC Space-write and the end-user authorization demonstration as explicit later-unit acceptance gates.
