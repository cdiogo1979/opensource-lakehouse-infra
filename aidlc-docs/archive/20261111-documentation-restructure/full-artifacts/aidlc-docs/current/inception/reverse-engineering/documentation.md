# Focused Reverse Engineering — Documentation

## Current README (589 lines, 13 sections)
Organized by mechanism: Components, Quick start, Compose modules, Users and sign-in, Data layout, Data products (create, remove), Adding users, Services (Keycloak, Polaris, RustFS, JupyterHub, Airflow, StarRocks, Jenkins), Workload Python environment, Streaming checkpoints, Operations (status, reset, backup, secrets, bootstrap steps), Scripts, Known limitations.

## Navigation problems
- No entry by role: an analyst must read the StarRocks service section to find how to connect; a developer's journey spans JupyterHub, Airflow, the workload environment and streaming checkpoints; the admin's spans Quick start, Operations, Data products and Adding users.
- Long mechanism detail (DAG factory internals, broker, Jenkins Job DSL) sits next to how-to steps.
- No overview of how the components fit together (identity, catalog, storage, compute, orchestration, CI).
- No history: why the platform looks as it does lives only in `aidlc-docs/archive/`.

## Platform evolution (from 27 archived intents)
1. **Pre-v2 (2026-10-23 to 10-27)**: Hive Metastore with Kerberos and Dremio replacing Nessie; StarRocks OSS over Hive; Dremio removed; Airflow 3 with Jenkins and ephemeral Spark; FreeIPA identities.
2. **v2 rebuild (10-28 to 10-31)**: Keycloak, Apache Polaris, RustFS and Spark replace FreeIPA and Hive; catalog and path layout; Jupyter user tokens; Airflow SSO and the writer token broker; RustFS console OIDC; Jenkins SSO; environment reset and bootstrap users.
3. **Multi-product platform (11-09 to 11-10)**: modular Compose; data product files and scripts; per-product Airflow bundles; StarRocks with Polaris catalogs and LDAP logins; per-product Jenkins pipelines; the platform DAG factory; the Spark session helper; the shared workload Python environment; repository renames.
4. **Workload capabilities and hardening (11-11)**: workflow subprojects and medallion layers; streaming checkpoints; StarRocks metadata access; reconciler recovery.
5. **Method**: AI-DLC (`.claude/skills/aidlc-workflows`) throughout: each change an intent with stages and approvals, an audit, canonical knowledge in `aidlc-docs/knowledge/`, and an archive per intent.
