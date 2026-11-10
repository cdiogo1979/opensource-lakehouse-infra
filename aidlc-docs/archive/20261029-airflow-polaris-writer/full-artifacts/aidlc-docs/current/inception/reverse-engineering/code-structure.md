# Code Structure

## Active v2 Airflow Files
- infra/airflow/Dockerfile: pinned Airflow 3.3.2/Python 3.10 image with Git, Docker, FAB, and Postgres providers.
- infra/airflow/airflow-entrypoint.sh: startup validation and runtime path/keytab setup.
- infra/airflow/validate-bundle-config.py: enforces exactly lakehouse-main/main and lakehouse-uat/uat, provider, Git connection, refresh, and sparse paths.
- infra/airflow/bootstrap-airflow-admin.py and airflow-secret-command.py: admin bootstrap and file-backed database secret support.
- scripts/provision-airflow-secrets.sh: idempotent Airflow secret-file creation.
- scripts/verify-airflow-environment-dags.sh: waits for UAT and production DAGs.
- docker-compose.deferred.yml: inventory only; not included in standard startup.
- infra/keycloak/realm-contract.json and bootstrap-realm.py: identity/group contract.
- infra/polaris/oidc.properties and bootstrap-product-authorization.py: OIDC and catalog grants.

## Protected Workload Source
Current DAG factory, DAGs, environment configs, Spark runtime, and tests are in sibling opensource-lakehouse. Its guide documents three bundles and a writer Kerberos-keytab workload contract. The user authorizes changing only dags/dag_factory.py in that repository. Bundle JSON, DAG declarations, configs, notebooks, and all other repository files remain unchanged unless separately approved.
