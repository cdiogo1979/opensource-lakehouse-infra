# Components

For everyone: how the platform's parts fit together and which Compose modules run them. Back to the [README](../README.md).

## How the parts fit together

| Concern | Component | In one line |
|---|---|---|
| Identity | **Keycloak** with **LDAP** | One set of groups and one password per person for every app; see [Identity](reference/identity.md) |
| Catalog and permissions | **Apache Polaris** | The Iceberg REST catalog; checks every table access against the product's grants and hands out short-lived storage credentials; see [Polaris](reference/polaris.md) |
| Storage | **RustFS** | S3-compatible buckets, three per product; no workload gets root keys; see [RustFS](reference/rustfs.md) |
| Interactive compute | **JupyterHub** with Spark | Notebooks that read and write as the signed-in user; see [JupyterHub](reference/jupyterhub.md) |
| Scheduled compute | **Airflow** with Spark | DAGs the platform builds from each product repository's workflow files; each run writes as the product's writer; see [Airflow](reference/airflow.md) |
| SQL and BI | **StarRocks** | SQL over the same Iceberg tables, with each user's own permissions, and materialized views that accelerate queries; see [StarRocks](reference/starrocks.md) |
| CI | **Jenkins** | One folder per product, building its repository's prod and UAT branches and its pull requests; see [Jenkins](reference/jenkins.md) |
| Change workflow | **AI-DLC** | Every change to the platform is an intent: planned, approved stage by stage, recorded, and closed into the canonical design; see [AI-DLC](reference/aidlc.md) |
| Workload code | the **workload Python environment** and `lakehouse_spark` | The same Python 3.10 packages in Airflow and Jupyter, and the platform's Spark session; see [Workload Python environment](reference/workload-python.md) |

**Access everywhere follows the same Keycloak groups** (the whole security model: [Security](security.md)). A group change reaches Polaris and StarRocks through the scheduled reconciler (every five minutes), and JupyterHub, Airflow and Jenkins at the next sign-in.

## Compose modules

The stack is one Compose project, `lakehouse-local`, split into module files. `scripts/lakehouse.sh` combines them.

| File | Module | Services | Runs |
|---|---|---|---|
| `compose.core.yml` | Core | Keycloak and its database, Polaris and its database, schema init, the scheduled group reconciler, RustFS | always |
| `compose.jupyter.yml` | Jupyter | JupyterHub and per-user Spark servers | unless `JUPYTER_ENABLED=false` |
| `compose.jenkins.yml` | Jenkins | Jenkins | unless `JENKINS_ENABLED=false` |
| `compose.starrocks.yml` | StarRocks | StarRocks FE and BE | unless `STARROCKS_ENABLED=false` |
| `compose.airflow.yml` | Airflow | Airflow and its writer token broker | through `start-airflow`, `airflow-status`, and `stop-airflow` |

- **Opt-outs**: set the flags in `.env`. A disabled module is not started, shown in `status`, or stopped, and its volumes are kept.
- **Core dependency**: every module needs core. When you run Compose yourself, always pass `compose.core.yml` first:

  ```sh
  docker compose -f compose.core.yml -f compose.jenkins.yml logs -f jenkins
  docker compose -f compose.core.yml -f compose.starrocks.yml ps
  ```

- **Orphan warnings and rebuilds**: a manual command that leaves out some modules makes Compose call the other modules' containers "orphans". **Never** add `--remove-orphans`, because it deletes them. Set `COMPOSE_IGNORE_ORPHANS=true` to hide the warning. If you rebuild images by hand, set `BUILDX_NO_DEFAULT_ATTESTATIONS=1`, as the scripts do, so unchanged images keep their ID and containers are not recreated.
- **Other settings**: ports, memory limits, and the startup timeout (`STARTUP_TIMEOUT_SECONDS`, default 600) are in `.env.example`.

## Data products

Where each product's data lives, the product file, access levels and materialized views: [Data products](reference/data-products.md).
