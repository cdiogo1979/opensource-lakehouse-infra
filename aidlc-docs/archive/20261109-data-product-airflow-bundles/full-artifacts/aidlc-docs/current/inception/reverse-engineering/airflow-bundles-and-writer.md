# Airflow Bundles and the Writer — Focused Reverse Engineering

## How the bundles are configured today (this repository)
- **One fixed pair of bundles**: `scripts/setup/airflow-bundle-config.py` renders a JSON list for one repository (`LAKEHOUSE_BUNDLE_REPOSITORY_URL`, default `https://github.com/cdiogo1979/opensource-lakehouse.git`):
  - `lakehouse-main` tracks `main`; `lakehouse-uat` tracks `uat`
  - `GitDagBundle`, `git_conn_id=lakehouse_git` (a credential-free connection created by `infra/airflow/ensure-git-connection.py`), `refresh_interval=300`, `sparse_dirs=[dags, configs, notebooks]`
- **Delivery**: `scripts/lakehouse.sh` exports the list as `LAKEHOUSE_BUNDLE_CONFIG_LIST`, which Compose passes to every Airflow service as `AIRFLOW__DAG_PROCESSOR__DAG_BUNDLE_CONFIG_LIST`. **Changing the list means recreating the Airflow services.**
- **Validation**: `infra/airflow/validate-bundle-config.py` (run by `start-airflow` and inside the image) accepts exactly `lakehouse-main` and `lakehouse-uat` from one repository. Any other list fails.
- **Checkouts**: bundles are cloned into `.runtime/airflow-dag-bundles/<bundle-name>/`.
- **Product files**: `data-products/*.yaml` have no repository or Airflow settings yet.

## How the workload repository uses them (`opensource-lakehouse`, read from the local checkout)
- **Environment from the bundle name**: `dags/dag_defaults.py` maps the bundle name to the environment by fixed names:
  - `lakehouse-main` or `lakehouse-prod` → DAG prefix `main`, environment `prod`
  - `lakehouse-uat` → `uat`
  - **any other name → `dev`**
- **Targets from fixed configs**: `configs/prod.yml` (and `uat.yml`, `dev.yml`) fix the targets, for example `catalog_name: lakehouse`, `database_name: default_lh`, `storage_path: s3a://bucket-default/`.
- **DAG IDs**: they are built from the prefix and the workload name. **Two bundles of the same repository produce the same DAG IDs.** Airflow requires a DAG ID to be unique across bundles, so they would collide.
- **Writer token**: each run registers with the broker (`POST /v1/runs` with `{dag_id, run_id}` and the scheduler's control token). The payload names **no product or identity**.

## The writer broker (`infra/airflow-token-broker/app.py`)
- **One identity**: it serves exactly one writer, configured by environment: `KEYCLOAK_WRITER_USERNAME=srv-default-writer`, its password file, and the `lakehouse-writer` client.
- **Hard-coded check**: it also checks that the token carries the `role-default-writer` role.
- **No per-product choice is possible today**: the request carries no product, and the broker holds one credential.

## Writer identities available
- **Per product**: since the data product intent, each product has a writer user `srv-<p>-writer` (in its writer group, password file `.runtime/credentials/srv-<p>-writer-password`, in LDAP since the last intent).
- **Airflow secrets**: Airflow reads secrets through `airflow-secret-command.py` and Docker secrets.

## What this means
1. **The repo setting is infrastructure-side.** A `repo` block in the product file (URL, prod branch, UAT branch) can drive `airflow-bundle-config.py`: two bundles per product with a repo, for example `<p>-prod` and `<p>-uat`. `validate-bundle-config.py` and the start and apply flows must accept that list.
2. **"Executing" the bundles** after a product apply needs the Airflow services recreated with the new list. Airflow then clones the repository and parses its DAGs, and the bundle refreshes every 300 s. Whether DAG runs should also be triggered is a requirement question.
3. **Constraints from the workload repository (not changed by this intent)**:
   - **Environment**: bundles not named `lakehouse-main`, `lakehouse-prod`, or `lakehouse-uat` are treated as `dev`.
   - **Targets**: the configs target the `default` product's catalog, namespace, and bucket.
   - **Same repository twice**: the testing product's bundles would produce the **same DAG IDs** as `default`'s, so the two cannot be loaded together unless names or prefixes differ.

   A testing product can still register its bundles, but its DAGs would collide or run against `default`'s targets until the workload repository supports products.
4. **A per-product write credential** needs the broker to hold several writer credentials and to pick one per run. The run registration names no product, so the broker would need the product: the DAG's bundle name, sent by the workload code (a workload repository change), or looked up from Airflow. A product-file setting such as `airflow.writer_secret` can name the credential, but nothing can use it without that link.
