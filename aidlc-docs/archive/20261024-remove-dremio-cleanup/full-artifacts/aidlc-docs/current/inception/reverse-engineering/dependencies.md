# Reverse Engineering — Dependencies and Coupling

## Direct Dremio dependencies

1. Compose runtime: Dremio service, image, ports, mounts, keytab, network, `dremio-data` volume, and Dremio writer-password secret.
2. Kerberos: KDC creation and healthcheck for `dremio@REALM`; identity provisioner loop and extraction ACL.
3. Hive: `hadoop.proxyuser.dremio.hosts` and `hadoop.proxyuser.dremio.users` in the core-site template.
4. TPCH workload: `tpch-jdbc` service, Dremio JDBC driver copied from a Dremio image in the loader Dockerfile, Dremio client code and runtime secrets.
5. Local orchestration: bootstrap-created Dremio admin/writer/user passwords, provisioning restart of Dremio, and startup URL output.
6. Documentation and examples: README, Dremio SQL matrix, canonical knowledge documents, previous intent archive and current closeout state.

## Data and state dependencies

Shared persistence includes `object-store-data`, `metastore-db-data`, `kerberos-kdc-data`, JupyterHub/user work volumes, `.runtime/credentials`, `.runtime/hive-conf`, and `.runtime/workload`. The Dremio named volume and Dremio credential/keytab files are separately identifiable. Removing all Compose volumes would also destroy Hive metadata, KDC identities, RustFS data, and notebook workspaces; that is outside the default safe cleanup boundary.

## External interface

There is no application HTTP API implemented in this repository. Compose exposes Dremio UI/JDBC/Flight, RustFS console/S3, Spark UI, and JupyterHub endpoints. Hive Thrift, PostgreSQL, and Kerberos services are internal to the Compose network. The Dremio JDBC interface is consumed by the optional `tpch-jdbc` one-shot workload.
