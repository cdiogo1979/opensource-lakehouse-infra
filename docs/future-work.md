# Future work

For everyone: components and improvements under consideration. These are **proposals, not decisions**; each would become its own AI-DLC intent with requirements, probes and approvals ([Platform evolution](evolution.md)). Back to the [README](../README.md).

## New components

### Governance: OpenMetadata

A data catalog and governance layer over the data products.

| What it would add | How it would fit |
|---|---|
| A searchable catalog of every product's tables, columns, owners and descriptions | Metadata ingestion from the Polaris Iceberg catalogs and StarRocks |
| Lineage from source to bronze, silver and gold, and to materialized views | Ingestion from Airflow runs and Spark jobs |
| Ownership, a business glossary, tags and classifications (for example personal data) | Owners from the product files' groups; tags maintained by product owners |
| Data quality tests and their results next to each table | Tests per product, alongside its workflows |
| Single sign-on and roles | Keycloak OIDC with the product groups, like the other apps |

Questions to settle first: which OpenMetadata release supports Polaris (Iceberg REST) and StarRocks ingestion, how its roles map to the product groups without widening access, and its memory footprint on one machine (it brings its own database and search engine).

### Observability

Today each service has its own logs and health checks, and `./scripts/lakehouse.sh status` shows container health. A shared observability stack would add:

| What it would add | Candidate |
|---|---|
| Metrics: service health, Spark and Airflow run durations, broker renewals, StarRocks queries, storage use | Prometheus (the Airflow token broker already exposes Prometheus metrics) |
| Dashboards and alerts, for example a failed reconciler cycle, an unhealthy RustFS, or a run near its memory limit | Grafana |
| Central, searchable logs from every container and Spark run, with the same redaction as today | Loki (or OpenSearch) |
| Traces across Airflow, Spark, Polaris and RustFS | OpenTelemetry |

Questions to settle first: the memory budget next to Spark and StarRocks, and keeping secrets out of collected logs and metrics.

### Running on Kubernetes

Today the platform is one Docker Compose project on one machine, so every component shares its CPU and memory, and Spark runs in one container per Airflow run or Jupyter server. Moving to Kubernetes would let the components scale:

| What it would add | How it would fit |
|---|---|
| Spark that scales with the work: executors started per job and released after it | Spark on Kubernetes (driver and executor pods), instead of `local[*]` in one container; this also removes the shared-container memory limit of a DAG run. The Spark runtime image would need Spark's Kubernetes jars back (removed as unused) |
| Airflow tasks as separate pods | Airflow's Kubernetes executor, so tasks no longer compete inside the scheduler |
| Jupyter servers with their own resource requests and limits | JupyterHub's KubeSpawner |
| Horizontal scaling of stateless services and StarRocks | Replicas and autoscalers for Polaris, Keycloak, the token brokers and StarRocks compute nodes; cluster autoscaling for the nodes |
| Managed configuration and secrets | Helm charts or an operator per component; Kubernetes Secrets or an external secrets manager instead of `.runtime/credentials/` |

Questions to settle first: what stays the same contract for data products (product files, workflow JSON, `lakehouse_spark`), how the token brokers and checkpoint keys map to pods and service accounts, storage for RustFS and the databases (or a managed object store), TLS and ingress for the browser sign-ins (which would also end the local-only HTTP limit), and whether a local cluster (kind, k3d, Rancher Desktop) remains the development setup.

## Platform improvements already identified

Recorded as follow-ups during earlier intents:

| Improvement | Why |
|---|---|
| A per-workflow parallelism limit and per-job Spark memory | A run's tasks share one Spark container; too many at once run it out of memory |
| A higher Jupyter memory limit | Each Spark notebook holds 1 to 1.5 GiB of a server's 2 GiB |
| Workflow parameters at trigger time | Change, for example, a reprocessing window without editing the workflow file |
| Materialized-view authoring in the developer journey, and verifying query rewrite | Make acceleration a documented, tested practice |
| Verify storage-credential refresh for long writes | A single Iceberg write over about 50 minutes is not verified |
| A least-privilege identity for the reconcilers | They use the Keycloak administrator today |
| Restart JupyterHub when the product model changes | The Hub keeps the model it started with |

Current status of the follow-ups: `aidlc-docs/current/aidlc-state.md`.
