# Reverse Engineering — Interfaces

This project does not implement a standalone application API. Its interfaces are service protocols and one-shot workload clients:

- Hive Metastore Thrift: internal `hive-metastore:9083`, Kerberos/SASL enabled.
- PostgreSQL: internal `metastore-db:5432`, used by Hive Metastore.
- RustFS: S3-compatible API at `object-store:9000`; web console at `9001`.
- Kerberos: KDC and admin service internal to the Compose network.
- Spark: local workload and UI; the TPCH loader writes through Hive catalog and RustFS.
- JupyterHub: local browser endpoint on `127.0.0.1:8008` with development-only DummyAuthenticator.
- Dremio: UI `9047`, JDBC `31010`, Flight `32010`, coordinator `45678`; Dremio JDBC is consumed by `tpch-jdbc` and is in removal scope.

After Dremio removal, its endpoints and JDBC client should no longer be present. Retained endpoint bindings must remain loopback-only as configured today.
