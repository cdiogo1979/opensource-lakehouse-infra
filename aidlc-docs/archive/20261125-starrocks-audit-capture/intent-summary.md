# Intent Summary: StarRocks Audit Capture

## Intent
StarRocks Audit Capture (`20261125-starrocks-audit-capture`)

## Objective
Platform support for the audit data product's StarRocks source: AuditLoader capture into a 7-day staging table, platform_sources grants, and lakehouse_starrocks.connect() for workload code in Airflow runs and Jupyter.

## Date
2026-11-26

## Scope
Included: vendored AuditLoader 5.0.0 and its lifecycle in the StarRocks bootstrap, srv-auditloader, fe.conf login events, platform_sources and table grants, audit.yaml, lakehouse_starrocks with PyMySQL, CA and settings in Airflow run containers and Jupyter servers, tests, docs. Excluded: the audit product's own pipeline (paired intent 20261125-starrocks-query-audit in opensource-lakehouse-audit-dp), a full workload re-lock, the pre-existing grant re-application.

## Units / workstreams
U1 starrocks-audit-capture, U2 product-platform-sources, U3 workload-starrocks-connection

## Major requirements
- Capture every StarRocks audit event (queries, slow queries, logins, logouts) into starrocks_audit_db__.starrocks_audit_tbl__, 7 days, UTC
- srv-auditloader with INSERT on the staging table only; generated password, never in the repository or logs
- platform_sources.starrocks_audit in product files grants SELECT; audit.yaml: owner, developer, writer read, analyst none
- lakehouse_starrocks.connect(): writer token in Airflow, user password in Jupyter, verified TLS

## Architecture and design decisions
- AuditLoader 5.0.0 vendored with a SHA-256 lock (no versioned GitHub releases exist)
- Capture runs on every start in bootstrap-starrocks --runtime-only; reinstall only when the built package digest changes
- Plugin package bind-mounted read-only into the FE; FE plugin folder on the starrocks-fe-plugins volume
- Table-level grants (TABLE db.table) through the existing grant planning
- AuditLoader secret_key encryption not used (its key would sit next to the password)

## Implementation decisions
- Capture failures are reported, not fatal, so start brings up the rest
- StarRocks certificates created before JupyterHub (the Hub mounts the CA)
- Lock: only the PyMySQL line added; the lock script's 7 transitive bumps left for maintenance
- Spawner CA check in lakehouse_policy.starrocks_ca_volume; Jupyter StarRocks user from the validated preferred_username

## Deviations
- Requirements Q2:A (download a pinned GitHub release) superseded by vendoring (no releases exist)
- Jupyter login first used JUPYTERHUB_USER (the Keycloak ID); fixed in Build and Test to the Keycloak username
- The Hub image bakes its config and spawner, so Build and Test needed a Hub image rebuild
- Rancher Desktop deleted unused images under disk pressure; build cache pruned with the user's approval

## Verification
construction/build-and-test/build-and-test-summary.md: host pytest 730 passed, 3 skipped; dag-factory-tests 119 passed; broker tests 13 passed; docs links and compose config OK; images rebuilt and parity OK; live checks 10/10 PASS on the local stack, including the audit product's uat loads and the user's Jupyter login.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse-infra/functional-design/starrocks-sql-access.md
- aidlc-docs/knowledge/opensource-lakehouse-infra/functional-design/lakehouse-product-access.md
- aidlc-docs/knowledge/opensource-lakehouse-infra/functional-design/workload-python-environment.md
- aidlc-docs/knowledge/opensource-lakehouse-infra/functional-design/airflow-workflows.md

## Superseded decisions
- Download a pinned GitHub release at bootstrap -> vendored package with lock (application design AD-1)
- AC-18 Jupyter user = JUPYTERHUB_USER -> LAKEHOUSE_STARROCKS_USER from preferred_username
- AC-5 checksum mismatch stops the bootstrap -> reported, bootstrap continues, nothing installed

## Archived artifacts
- aidlc-docs/archive/20261125-starrocks-audit-capture/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261125-starrocks-audit-capture/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261125-starrocks-audit-capture/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261125-starrocks-audit-capture/full-artifacts/infra/starrocks/audit_capture.py
- aidlc-docs/archive/20261125-starrocks-audit-capture/full-artifacts/infra/starrocks/plugins/auditloader.lock
- aidlc-docs/archive/20261125-starrocks-audit-capture/full-artifacts/infra/workload-python/python/lakehouse_starrocks.py
- aidlc-docs/archive/20261125-starrocks-audit-capture/full-artifacts/data-products/audit.yaml

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261125-starrocks-audit-capture/full-artifacts/`
