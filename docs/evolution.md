# Platform evolution

For anyone who wants to know why the platform looks the way it does. The big picture only; every change has a full record in `aidlc-docs/archive/`. Back to the [README](../README.md).

## The method: AI-DLC

The platform has been built with the **AI-DLC** (AI-Driven Development Life Cycle) workflow (`.claude/skills/aidlc-workflows`), with an AI assistant doing the work and a person approving each step.

- **Intents**: every change is an *intent*, such as "add streaming checkpoints". An intent goes through stages: inception (workspace detection, reverse engineering, requirements, workflow planning, design), construction (functional design, code generation, build and test), and a deploy handoff. Stages that add nothing are skipped.
- **Approvals**: each stage ends with a review; nothing moves on without an explicit approval. Questions are asked as multiple choice, with a recommended option.
- **Probes**: when a design depends on behavior nobody has verified (a token flow, a storage permission), a short, reversible experiment settles it before anything is built.
- **Records**: `aidlc-docs/current/` holds the open intent's documents, its state (`aidlc-state.md`) and its audit (`audit.md`, every input and decision with a timestamp).
- **Knowledge**: when an intent closes, what is now true is written into the canonical design in `aidlc-docs/knowledge/` (one application design, one functional design per component), and the full intent is archived in `aidlc-docs/archive/<intent-id>/` with a short summary. `scripts/aidlc_intent.py compact` does the closing.

The same method runs in the data product repository (`opensource-lakehouse-sample-dp`). How to use it today: [AI-DLC: the change workflow](reference/aidlc.md).

## Phase 1 — First stack: Hive, Kerberos, Dremio (2026-10-23 to 10-27)

The starting point was a Nessie-based lakehouse. The first intents tried a classic enterprise stack, which taught what the platform needed but proved heavy to run locally.

| Intent | Outcome |
|---|---|
| [Hive, Dremio and Kerberos](../aidlc-docs/archive/20261023-hive-dremio-kerberos/intent-summary.md) | Hive Metastore replaced Nessie, with Kerberos identities and Dremio on top |
| [StarRocks OSS](../aidlc-docs/archive/20261024-integrate-starrocks-oss/intent-summary.md) | StarRocks as the analytical SQL engine over Hive and Iceberg |
| [Dremio removed](../aidlc-docs/archive/20261024-remove-dremio-cleanup/intent-summary.md) | One SQL engine fewer; the Hive, RustFS, Spark and Jupyter core kept |
| [Airflow, Jenkins and Spark](../aidlc-docs/archive/20261026-integrate-airflow-jenkins-spark/intent-summary.md) | Airflow 3 Git DAG bundles with ephemeral Spark containers, and Jenkins validation |
| [Central identity with FreeIPA](../aidlc-docs/archive/20261027-central-identity-environment-roles/intent-summary.md) | Environment-scoped roles for storage and Spark through FreeIPA |

## Phase 2 — The v2 rebuild: Keycloak, Polaris, RustFS (2026-10-28 to 10-31)

Kerberos and FreeIPA were replaced by OIDC tokens, and Hive by a REST catalog that checks permissions and hands out short-lived storage credentials. This is the architecture the platform still has.

| Intent | Outcome |
|---|---|
| [Keycloak, Polaris and the catalog bootstrap](../aidlc-docs/archive/20261028-keycloak-polaris-catalog-bootstrap/intent-summary.md) | Keycloak, Apache Polaris, RustFS and Spark replace FreeIPA and Hive, with a platform-admin journey |
| [Catalog and path layout](../aidlc-docs/archive/20261028-polaris-database-path-layout/intent-summary.md) | The catalogs `lakehouse`, `lakehouse_uat`, `lakehouse_dev` and `<bucket>/<catalog>/<database>/<table>` paths |
| [JupyterHub with user tokens](../aidlc-docs/archive/20261028-jupyterhub-polaris-developer-token/intent-summary.md) | Notebooks read and write as the signed-in user through Polaris |
| [Airflow writer tokens](../aidlc-docs/archive/20261029-airflow-polaris-writer/intent-summary.md) | A private token broker: runs write as a service identity without seeing its credentials |
| [RustFS console sign-in](../aidlc-docs/archive/20261030-rustfs-keycloak-oidc/intent-summary.md) | Console access by Keycloak group (Airflow and Jenkins got Keycloak sign-in in the same days) |
| [Environment reset and bootstrap users](../aidlc-docs/archive/20261031-environment-reset-bootstrap-users/intent-summary.md) | A tested reset and the two-step start with five default users |

## Phase 3 — A multi-product platform (2026-11-09 to 11-10)

The platform went from one hard-wired product to any number of **data products**, each defined by one YAML file, and moved DAG building out of product repositories.

| Intent | Outcome |
|---|---|
| [Modular Compose](../aidlc-docs/archive/20261109-cleanup-modular-compose/intent-summary.md) | Core plus optional jupyter, jenkins, airflow and starrocks modules |
| [Data product and user scripts](../aidlc-docs/archive/20261109-data-product-and-user-scripts/intent-summary.md) | Create, change and remove products from their files; create users |
| [Per-product Airflow bundles](../aidlc-docs/archive/20261109-data-product-airflow-bundles/intent-summary.md) | Each product names its repository and gets `<name>-main` and `<name>-uat` bundles and its own writer |
| [StarRocks on Polaris](../aidlc-docs/archive/20261109-starrocks-integration/intent-summary.md) and [LDAP logins](../aidlc-docs/archive/20261109-starrocks-ldap-login/intent-summary.md) | StarRocks catalogs on Polaris with product-aligned roles; one LDAP password for every app and StarRocks |
| [Per-product Jenkins pipelines](../aidlc-docs/archive/20261110-data-product-jenkins-pipelines/intent-summary.md) | A folder per product with CI and pull-request pipelines |
| [Platform DAG factory](../aidlc-docs/archive/20261110-platform-dag-factory/intent-summary.md), [Spark session helper](../aidlc-docs/archive/20261110-platform-spark-session-helper/intent-summary.md) and [shared workload environment](../aidlc-docs/archive/20261110-shared-workload-requirements/intent-summary.md) | Repositories hold only workflow JSON, notebooks and configs; the platform builds the DAGs, owns the Spark session, and pins one Python 3.10 environment for Airflow and Jupyter |

## Phase 4 — Workload capabilities and hardening (2026-11-11)

The first real medallion workload (TPC-H bronze and silver, in the sample data product repository) drove the platform's next capabilities and exposed operational gaps.

| Intent | Outcome |
|---|---|
| [Workflow subprojects](../aidlc-docs/archive/20261111-workflow-subprojects/intent-summary.md) | Workflows grouped by subproject, notebooks in medallion layer folders |
| [Streaming checkpoints](../aidlc-docs/archive/20261111-spark-s3-checkpoints/intent-summary.md) | Durable Structured Streaming checkpoints in each product's bucket (`s3ckpt://`, per-bucket keys) |
| [StarRocks metadata access](../aidlc-docs/archive/20261111-starrocks-metadata-access/intent-summary.md) | SQL clients such as DBeaver can list tables, with no access beyond each role |
| [Reconciler recovery](../aidlc-docs/archive/20261111-reconciler-starrocks-recovery/intent-summary.md) | The scheduled sync runs current code, restores StarRocks logins after a restart, and reports its health |

## What's next

See [Future work](future-work.md): governance with OpenMetadata, an observability stack, and the platform improvements already identified (tracked in `aidlc-docs/current/aidlc-state.md`).
