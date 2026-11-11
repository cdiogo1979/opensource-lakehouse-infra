# Requirements — Documentation Restructure

## Intent Analysis
- **Request**: make the platform documentation easy to navigate: clear components; user journeys for the platform admin, the data product owner, the data product developer and the data analyst / BI user; a big-picture platform evolution (the AI-DLC framework, then the main intents; small intents left out). Deliver a separate README for review before replacing the current one.
- **Type**: documentation only; no code, configuration or behavior change. **Depth**: standard.

## Functional Requirements
- **FR-1 Draft, not replacement**: the new documentation is written as `README.draft.md` plus `docs-draft/`; the current `README.md` and every other file stay unchanged until the user approves the switch (then the draft replaces them in a later step of this intent).
- **FR-2 Landing page** (`README.draft.md`, short): what the platform is, an architecture diagram (Mermaid, with a text alternative), the component table, the quick start, "Start here" links by role, and links to every other page.
- **FR-3 Components** (`docs-draft/components.md`): each component's role, URL, Compose module, and how it connects to identity, catalog and storage; the data layout (catalogs, namespaces, buckets, paths) and the data product file.
- **FR-4 Journeys** (`docs-draft/journeys/`), each as tasks in the order a person meets them, linking to reference detail instead of repeating it:
  - `platform-admin.md`: start, bootstrap, users, data products (create, change, remove), operations (status, reset, backup, secrets, rotation), troubleshooting;
  - `data-product-owner.md`: the product file and its access levels, people in groups, Jenkins folder, Airflow, approving and promoting changes (uat to main);
  - `data-product-developer.md`: Jupyter, the product repository contract (workflows, notebooks, configs, requirements; the detailed structure is in the sample data product repository, CR-2), Spark sessions, streaming checkpoints, Airflow runs, CI, and **StarRocks materialized views**: developers author them (in dev; the MV databases and levels, as documented today) to accelerate queries;
  - `data-analyst.md`: StarRocks logins, DBeaver and BI tools, browsing catalogs, what analysts can and can't see, and how materialized views speed up their queries (StarRocks rewrites matching queries to use them; analysts query the tables as usual), with a link to the developer journey for authoring.
- **FR-5 Reference** (`docs-draft/reference/`): the detail moved out of the journeys, by component (Keycloak and LDAP, Polaris, RustFS, JupyterHub, Airflow and the DAG factory, StarRocks, Jenkins, the workload Python environment, streaming checkpoints), plus scripts and known limitations.
- **FR-6 Evolution** (`docs-draft/evolution.md`): the AI-DLC method (intents, stages, approvals, audit, canonical knowledge, archive), then four phases (pre-v2 Hive/Kerberos/Dremio; v2 rebuild on Keycloak, Polaris and RustFS; the multi-product platform; workload capabilities and hardening), each with why it happened and 3 to 6 main intents in one line each, linking to their archive summaries.
- **FR-7 Nothing lost**: every fact, command and limitation of the current README appears in the draft (checked section by section in Build and Test).

## Change Record
- **CR-2** (user, Requirements Analysis): the developer journey points to the sample data product repository (`opensource-lakehouse-sample-dp`, https://github.com/cdiogo1979/opensource-lakehouse-sample-dp) for the detailed repository structure (subprojects, layers, notebook standard, naming conventions, helpers); the platform documentation keeps only the platform-side contract and links there.
- **CR-1** (user, Requirements Analysis): materialized views are available to everyone and are part of query acceleration through StarRocks' query rewrite. Authoring belongs to the developer journey (a follow-up intent integrates it fully); the analyst journey and the component overview describe the acceleration (queries on the tables are rewritten to use matching materialized views). The draft states this as the design; the follow-up verifies the rewrite behavior on the platform.

## Non-Functional Requirements
- **NFR-1 Navigation**: every page starts with one line saying who it is for and links back to the landing page; no page is more than two links from the landing page.
- **NFR-2 Valid content**: Mermaid validated; relative links resolve in the draft tree.
- **NFR-3 Style**: the current README's style (short bullets, tables, commands in code blocks).

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No (documentation only) | Requirements Analysis |
| Property-Based Testing | No (no code) | Requirements Analysis |
| Resiliency Baseline | No | Requirements Analysis |
| Workflow Conventions | Yes (always enforced) | Workflow start |
