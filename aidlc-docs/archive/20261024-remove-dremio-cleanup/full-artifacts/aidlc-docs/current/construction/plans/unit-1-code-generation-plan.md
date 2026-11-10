# Code Generation Plan — Unit 1 Dremio Removal

This plan is the single source of truth for implementation. It follows the approved requirements, execution plan, Functional Design, and Infrastructure Design. Do not delete or alter retained platform data, credentials, principals, or volumes.

## Unit Context

- **Unit:** Remove Dremio integration while preserving the local Hive/RustFS/Spark/Jupyter lakehouse workload.
- **Stories:** None; User Stories was skipped for this internal infrastructure cleanup.
- **Dependencies:** Existing Docker Compose project, Hive Metastore, PostgreSQL, Kerberos, RustFS, Spark, JupyterHub, and TPCH workload.
- **Contracts:** Spark TPCH ETL continues to create/validate the existing Hive catalog tables in RustFS. Dremio services, JDBC, Spaces/views, and Dremio-only identities are removed.
- **Data entities:** Existing Hive databases/tables, Iceberg objects, and ignored runtime TPCH inputs remain unchanged. Redundant root copies of those TPCH inputs are removed after byte comparison.
- **Service boundaries:** Existing Compose services remain; no replacement query engine is introduced.
- **PBT:** No pure helper or serialization round-trip is intended to change. If implementation changes such logic, stop and add PBT steps for the applicable invariants before proceeding.

## Exact Workspace Paths

### Modify

- `docker-compose.yml`
- `.env.example`
- `.env` — remove only `DREMIO_*` setting lines; never display or rewrite unrelated values.
- `infra/hive/core-site.xml.in`
- `infra/kerberos/entrypoint.sh`
- `infra/kerberos/healthcheck.sh`
- `infra/identity-provisioner/provision-kerberos-identities.sh`
- `infra/tpch-loader/Dockerfile`
- `infra/tpch-loader/run-workload.sh`
- `infra/tpch-loader/load_tpch.py`
- `infra/spark/spark-defaults.conf`
- `scripts/bootstrap-local.sh`
- `scripts/provision-identities.sh`
- `scripts/start.sh`
- `scripts/clean.sh`
- `scripts/run-tpch-workload.sh`
- `README.md`
- `aidlc-docs/knowledge/hive-dremio-rustfs/application-design.md`
- `aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/lakehouse-workload-and-access.md`

### Remove

- `infra/dremio/`
- `infra/tpch-loader/dremio_jdbc.py`
- `infra/tpch-loader/run-jdbc.sh`
- `sql/dremio-authz-matrix.sql`
- `spark/seed.py` — obsolete standalone Hadoop Catalog demo, unused by the retained Hive workload.
- `sql/queries.sql` — stale Dremio SQL examples for the removed demo catalog/schema.
- `tpch/data/*.tbl` — redundant root copies byte-for-byte identical to the ignored `.runtime/workload/tpch-data/*.tbl` inputs.

### Relocate

- `spark/spark-defaults.conf` → `infra/spark/spark-defaults.conf`
- `tpch/load_tpch.py` → `infra/tpch-loader/load_tpch.py`
- `tpch-generator/` → `infra/tpch-generator/`

Update all Compose, script, README, and active AI-DLC path references to match. Preserve `.runtime/workload/tpch-data/` and its files.

### Exact Local Runtime Files to Remove

- `.runtime/credentials/dremio-admin-password`
- `.runtime/credentials/dremio-writer-password`
- `.runtime/credentials/dremio-user-a-password`
- `.runtime/credentials/dremio-user-b-password`
- `.runtime/credentials/keytabs/dremio.keytab`

Runtime actions must be implemented as an explicit, narrowly scoped cleanup operation. Do not execute them during Code Generation. Preserve `aidlc-docs/archive/20261023-hive-dremio-kerberos/`, all other `.runtime/credentials` entries, generated Hive configuration, TPCH inputs/results, and Jupyter workspaces.

## Numbered Generation Steps

1. [x] **Compose and environment** — removed the Dremio service, `tpch-jdbc`, Dremio ports/image/volume/secret/mounts, and Dremio-only environment settings. Retained all other services, profiles, networks, and named volumes.
2. [x] **Kerberos and Hive configuration** — removed Dremio principal/keytab bootstrap, health checks, identity provisioning, ACL entries, and `hadoop.proxyuser.dremio.*` settings. Kept Hive and all workload/user identities.
3. [x] **TPCH image and workload** — removed the Dremio JDBC image stage, driver copy, Dremio client/JDBC runner, Dremio manifest fields and status path. Preserved Spark ETL schemas, table creation/validation, writer Kerberos flow, and RustFS access. Moved the loader and generator into `infra/` and updated Compose paths.
4. [x] **Bootstrap and lifecycle scripts** — stopped generating/checking Dremio passwords and starting/reporting Dremio. Rewrote `scripts/clean.sh` as a confirmation-gated Dremio-only cleanup that validates targets by Compose labels and references, removes only `dremio@<realm>` from the existing KDC, and targets only exact Dremio credential files. It fails closed when targets are ambiguous and never uses broad volume deletion.
5. [x] **TPCH invocation** — updated `scripts/run-tpch-workload.sh` to require only retained workload setup, run generator and Spark loader, and stop after successful ETL. Preserved run manifests and existing data.
6. [x] **Project documentation** — rewrote active README component, startup, identity, workload, endpoint, and cleanup guidance to describe the retained stack. Updated active reverse-engineering path references for relocated code. Historical archive records were not edited.
7. [x] **Canonical knowledge** — updated the two approved canonical design paths to remove Dremio as an active component and accurately describe the retained architecture/workload. No new canonical file was created.
8. [x] **Scope review** — inspected active source/configuration for operational Dremio dependencies; remaining source mentions are limited to the explicit one-time cleanup operation and migration documentation. Confirmed the approved preservation boundary; runtime cleanup has not been executed.

## Tests and Verification Artifacts

- No business-logic unit tests are planned because retained ETL logic is unchanged and no new pure helper is introduced.
- If any pure helper or serialization round-trip changes, revise this plan before that implementation and include PBT-02/03/07/08 as applicable.
- Build and Test will validate Compose/configuration and retained workload behavior according to the approved workflow; no runtime destructive operation is part of this generation plan.

## Completion Checklist

- [x] Steps 1–8 complete.
- [x] No Dremio runtime component remains in active Compose or retained workload/identity scripts.
- [x] Protected local state and archived history remain untouched during Code Generation.
- [x] Code generation changes are ready for user review before Build and Test.
