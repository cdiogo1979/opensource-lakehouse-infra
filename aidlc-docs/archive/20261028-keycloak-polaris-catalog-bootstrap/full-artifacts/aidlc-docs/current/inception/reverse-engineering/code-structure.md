# Code Structure

## Top-level layout
- `docker-compose.yml`: core stack and profiles for workloads, StarRocks, and identity provisioning.
- `docker-compose.freeipa-production.yml`: FreeIPA production-oriented overlay.
- `docker-compose.ranger-test.yml`, `docker-compose.starrocks-ldap-test.yml`: isolated experiments; do not treat as default runtime.
- `infra/`: component Dockerfiles, entrypoints, service configuration, bootstrap/reconciliation tools.
- `scripts/`: local bootstrap, startup, credentials, verification, and operations helpers.
- `aidlc-docs/`: workflow state, current intent and canonical/archived design documentation.
- `.env.example`: documented local variables. `.env` is present but was not read.

## Relevant implementation areas
- `infra/freeipa/`, `docker-compose.freeipa-production.yml`: FreeIPA image, initialization, readiness, identity and membership routines.
- `infra/kerberos/`, `docker-compose.yml` service `kdc`: standalone MIT KDC configuration and entrypoint.
- `infra/hive/`, `hive-schema-init`, `hive-metastore`, `metastore-db`: Hive schema/configuration, service image and PostgreSQL metadata database.
- `infra/bucket-init/`, `object-store`, `create-bucket`: RustFS and bucket initialization.
- `infra/identity-provisioner/`: Kerberos, RustFS, PostgreSQL, and role reconciliation.
- `infra/spark/`, `infra/jupyter/`: Spark runtime and JupyterHub/single-user images/configuration.
- `infra/airflow/`, `infra/jenkins/`: orchestration and CI images/entrypoints.
- `infra/starrocks/`: optional StarRocks FE/BE, SQL bootstrap, and LDAP integration experiments.

## Implementation observations
The setup is Compose-first, with imperative shell/Python bootstrap helpers and service-specific configuration templates. Persistent service state is held in named volumes. The new design should inventory and replace Hive references in every client/configuration path, and distinguish active FreeIPA-related code from isolated experiments before removing files.
