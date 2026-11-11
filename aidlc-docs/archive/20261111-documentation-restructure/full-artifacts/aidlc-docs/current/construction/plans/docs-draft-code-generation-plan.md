# Code Generation Plan — docs-draft

Workspace root `/Users/carlosdiogo/code_repo/opensource-lakehouse-infra`. New files only; nothing existing changes in this stage.

- [x] Step 1 — `README.draft.md`: what the platform is; Mermaid architecture with a text alternative; components table; quick start; "Start here" by role; map of all pages.
- [x] Step 2 — `docs-draft/components.md`: each component's role and connections (identity, catalog, storage, compute, orchestration, CI); Compose modules; data layout; the data product file and access levels; materialized views and query rewrite (CR-1).
- [x] Step 3 — `docs-draft/journeys/platform-admin.md`, `data-product-owner.md`, `data-product-developer.md` (with materialized-view authoring, CR-1, and the sample repository link, CR-2), `data-analyst.md` (logins, DBeaver and BI, browsing, acceleration).
- [x] Step 4 — `docs-draft/reference/`: `identity.md` (Keycloak, LDAP, users and groups), `polaris.md`, `rustfs.md`, `jupyterhub.md`, `airflow.md` (bundles, broker, DAG factory, workflow JSON), `starrocks.md`, `jenkins.md`, `workload-python.md`, `streaming-checkpoints.md`, `operations.md` (status, reset, backup, secrets, bootstrap steps), `scripts.md`, `limitations.md`.
- [x] Step 5 — `docs-draft/evolution.md`: AI-DLC method; four phases with main intents linked to their archive summaries.
- [x] Step 6 — `scripts/verify/docs-links.py` (new, read-only): checks relative links and anchors in a docs tree; run on the draft.
