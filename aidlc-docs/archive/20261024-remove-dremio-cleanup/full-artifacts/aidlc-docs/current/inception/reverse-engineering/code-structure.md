# Reverse Engineering — Code Structure

- `docker-compose.yml`: service graph, profiles, networks, named volumes, and file-backed secrets. Dremio-specific entries include the service, four published ports, `dremio-data`, writer-password secret, and `tpch-jdbc`.
- `infra/kerberos/`: KDC image, principal/keytab bootstrap, ACLs, and readiness checks. Both KDC entrypoint and healthcheck manage/validate Dremio's service identity.
- `infra/hive/`: Hive image and generated metastore/core-site templates. The core-site template includes Dremio proxy-user rules.
- `infra/dremio/`: Dremio server and Hive connector configuration; entirely Dremio-specific.
- `infra/identity-provisioner/`: component account provisioning. The Kerberos identity script creates `dremio` alongside workload identities.
- `infra/tpch-loader/`: Spark loader image and scripts. Its Dockerfile uses a Dremio image as a build stage to extract the JDBC driver; JDBC runner/client are Dremio-specific.
- `infra/tpch-loader/load_tpch.py`: Spark ETL into the Hive-backed Iceberg catalog and RustFS storage.
- `scripts/`: bootstrap generates Dremio admin/writer/test-user passwords; provisioning restarts Dremio; start prints Dremio URL; clean removes Dremio keytab and all volumes.
- `infra/spark/`: Spark service entrypoint and shared Spark configuration.
- `infra/tpch-generator/`: optional TPC-H input generation image and script.
- `infra/jupyter/`: JupyterHub, single-user image, and notebook examples.
- `.env.example`: Dremio port variables mixed with shared service port settings.
- `.runtime/`: ignored local secrets, generated Hive configs, workload inputs/results, and identity markers. Dremio passwords and keytab are present; this directory also contains non-Dremio credentials and data, so whole-directory deletion would remove unrelated local state.
- `aidlc-docs/knowledge/`: canonical design currently describes the prior Dremio-containing architecture and must be revised after the target residual system is approved.

There is no Git repository metadata in this project directory, so cleanup review cannot rely on `git status` or a tracked-file diff.
