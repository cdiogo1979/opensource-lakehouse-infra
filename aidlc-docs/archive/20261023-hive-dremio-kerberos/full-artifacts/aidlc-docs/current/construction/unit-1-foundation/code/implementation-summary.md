# Unit 1 Foundation — Code Generation Summary

## Generated foundation

- Replaced the active Nessie and Nessie PostgreSQL Compose services with a Hive Metastore, dedicated PostgreSQL database, schema initializer, and MIT Kerberos KDC.
- Added local ignored runtime credentials, protected PostgreSQL/Hive configuration generation, RustFS startup credentials, and a Hive service keytab lifecycle.
- Added Hive 3.1.3 Metastore configuration in `hive-site.xml` for PostgreSQL, SASL/Kerberos, the `_HOST` Hive service identity, `setugi`, and the RustFS warehouse path.
- Added Hadoop Kerberos authentication settings to `core-site.xml` and a dedicated Spark entrypoint that starts the Spark services and Jupyter without the image's unrelated Hive Thrift Server.
- Added a Hive image extension based on the pinned upstream Hive image with PostgreSQL JDBC 42.7.14 and Hadoop 3.1.0-matched S3A/AWS SDK dependencies.
- Replaced inline `pip install` and bucket-creation Python in Compose with a project-owned initializer and pinned Boto3 dependency. Bucket creation is ensure-only.
- Changed Spark's tracked catalog configuration from Nessie to an Iceberg Hive catalog, with the internal Thrift endpoint and RustFS path-style settings.
- Added lifecycle scripts for startup, non-destructive stop, and confirmation-gated full volume reset. Rewrote the operator README for the new foundation.
- Removed `spark/test-nessie.py` and `tpch/register_missing.py`. Preserved `spark/seed.py` as an explicitly standalone Hadoop Catalog example, outside the default startup path, and removed its hard-coded S3 credentials.

## Main application/configuration files

### Created

- `.gitignore`, `.env.example`
- `infra/kerberos/{Dockerfile,krb5.conf,kdc.conf,kadm5.acl,entrypoint.sh,healthcheck.sh}`
- `infra/hive/{Dockerfile,hive-site.xml.in,core-site.xml.in,schema-init.sh}`
- `infra/spark/entrypoint.sh`
- `infra/bucket-init/{Dockerfile,requirements.txt,ensure_bucket.py}`
- `scripts/{bootstrap-local.sh,render-metastore-config.py,stop.sh}`
- `aidlc-docs/current/construction/unit-1-foundation/code/implementation-summary.md`

### Modified

- `docker-compose.yml`, `.env`, `spark/spark-defaults.conf`, `spark/seed.py`, `scripts/render-metastore-config.py`
- `scripts/start.sh`, `scripts/clean.sh`, `README.md`

### Retired

- `spark/test-nessie.py`, `tpch/register_missing.py`
- Active Nessie/Nessie-database Compose services and persistent volume, the inline bucket setup command, and the default Nessie-dependent TPCH loader service.

## Runtime contracts

- Compose services: `kdc`, `metastore-db`, `hive-schema-init`, `hive-metastore`, `object-store`, `create-bucket`, `spark`, and `dremio`.
- Hive Thrift: `hive-metastore:9083` on the private Compose network.
- PostgreSQL: `metastore-db:5432`, database `metastore`, user `hive`; password supplied with a Compose file secret.
- Kerberos realm defaults to `LAKEHOUSE.LOCAL`; Unit 1 creates only `hive/hive-metastore@LAKEHOUSE.LOCAL` and its keytab.
- RustFS bucket and warehouse: `s3a://lake/warehouse/`; existing objects are not changed by bucket initialization.
- Host-published Dremio, RustFS and Spark ports bind to `127.0.0.1`.
- Normal stop preserves named volumes and runtime credentials. Full reset requires the exact confirmation phrase and removes the generated Hive service keytab so the KDC can recreate it.

## Limitations and verification status

- Build and Test passed the Unit 1 gates: PostgreSQL 16.14/Hive 3.1.3 schema initialization, healthy Metastore readiness under amd64 emulation, and Spark 3.5.5/Iceberg 1.8.1 Kerberos-authenticated namespace read/create/drop against Hive. See `aidlc-docs/current/construction/build-and-test/build-and-test-summary.md`.
- Dremio Hive source/effective-user behavior and cross-user authorization remain later integration gates.
- Hive storage authorization over RustFS and per-database authorization outcomes are not configured as proven behavior. `hive.metastore.execute.setugi` and SASL are candidate integration settings only.
- RustFS `1.0.0-glibc` was selected by immutable multi-platform digest because it is the available 1.0.0 multi-platform image. Registry tag/architecture were confirmed; API equivalence with the original `1.0.0` tag remains to be demonstrated.
- Current RustFS bootstrap credentials are local setup credentials. RustFS least-privilege policy behavior and separate setup/writer permissions remain unverified; Unit 2/3 must replace service use with component identities before ETL is treated as authorized.
- Unit 2 owns `admin`, `write-service-account`, `user_a` and `user_b` provisioning. Unit 3 owns writer-based sample databases/tables and Dremio JDBC objects. Units 4/5 own Dremio identity/source and Jupyter user-session integration.
