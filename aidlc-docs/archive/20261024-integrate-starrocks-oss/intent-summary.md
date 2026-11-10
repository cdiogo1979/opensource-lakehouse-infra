# Intent Summary: Integrate StarRocks OSS

## Intent
Integrate StarRocks OSS (`20261024-integrate-starrocks-oss`)

## Objective
Add StarRocks OSS as an analytical SQL engine over the existing Hive Metastore, Iceberg, and RustFS platform, with Kerberos service access, controlled SQL identities, and documented local operations.

## Date
2026-10-25

## Scope
Add opt-in StarRocks FE/BE runtime, Kerberos and RustFS service identity provisioning, an Iceberg HMS catalog and SQL access bootstrap, and operational guidance. Preserve Hive, PostgreSQL, RustFS, Spark, JupyterHub, existing data, credentials, and named volumes. Airflow/Jenkins integration remains out of scope.

## Units / workstreams
Unit 1 — Identity Provisioning, Unit 2 — StarRocks Runtime, Unit 3 — SQL Bootstrap and Catalog Access, Build and Test — closed with accepted limitations, Deploy Handoff — approved

## Major requirements
- Integrate StarRocks OSS with the existing Hive Metastore Iceberg catalog and RustFS object store.
- Provision a dedicated Kerberos service principal and RustFS identity for StarRocks.
- Provide SQL identities with documented least-privilege access, including a writer identity for controlled Iceberg DML.
- Preserve existing platform services, identities, credentials, data, and workspaces.

## Architecture and design decisions
- Keep Hive Metastore as catalog, RustFS as object storage, and Spark as the ETL engine; add StarRocks as an opt-in analytical SQL engine.
- Use a dedicated StarRocks Kerberos service identity for HMS access and a separate RustFS identity for object access.
- Use StarRocks native SQL users and grants for the documented databaseA/databaseB access matrix.
- Keep StarRocks FE/BE state in paired persistent named volumes and run a fail-closed paired-state preflight before startup.
- Keep SQL bootstrap host-side behind a non-secret diagnostics canary; do not expose secret-bearing SQL in command output.

## Implementation decisions
- Added opt-in StarRocks FE/BE Compose services and local images, startup health checks, loopback FE ports, and persistent volumes.
- Added identity provisioning for StarRocks Kerberos and RustFS access while preserving existing credential values.
- Added a SQL bootstrap flow for the iceberg catalog and native SQL users/grants.
- Configured Hive Metastore S3 filesystem aliases required for table creation against RustFS.
- Documented startup, access, tested reference resources, and verification limitations.

## Deviations
- Build and Test was closed under an explicit user-approved waiver; live ticket-refresh expiry behavior, Docker storage quota/growth, and lower FE/BE resource profiles remain unverified.
- The tested 2 CPU/2 GiB per FE/BE settings apply only to the documented read-only TPC-H Q1 profile and are not a proven minimum.
- The deployment handoff was approved, but no production deployment was performed.

## Verification
The user approved closing Build and Test with limitations on 2026-10-25. Documented checks passed for the runtime/catalog, SQL access matrix, reversible writer DML, Spark interoperability, state persistence after FE/BE recreation, read-only TPC-H Q1, the 2 CPU/2 GiB per-node reference profile, paired-state safety fixtures, and isolated ticket-refresh helper diagnostics. Live FE/BE ticket refresh behavior with a valid TGT through expiry, Docker Desktop storage quota/growth, and resource settings below 2 CPU/2 GiB per FE/BE remain unverified. This waiver records limitations and does not claim those checks passed. The deployment handoff was approved; no production deployment was performed.

## Canonical documents updated
- aidlc-docs/knowledge/hive-dremio-rustfs/application-design.md
- aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/lakehouse-workload-and-access.md

## Superseded decisions
- The previous active architecture described Hive/RustFS/Spark/Jupyter without StarRocks; this intent adds StarRocks as the analytical SQL service.

## Archived artifacts
- aidlc-docs/archive/20261024-integrate-starrocks-oss/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261024-integrate-starrocks-oss/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261024-integrate-starrocks-oss/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261024-integrate-starrocks-oss/full-artifacts/aidlc-docs/current/compaction/20261024-integrate-starrocks-oss/manifest.json
- aidlc-docs/archive/20261024-integrate-starrocks-oss/full-artifacts/aidlc-docs/knowledge/hive-dremio-rustfs
- aidlc-docs/archive/20261024-integrate-starrocks-oss/full-artifacts/docker-compose.yml
- aidlc-docs/archive/20261024-integrate-starrocks-oss/full-artifacts/.env.example
- aidlc-docs/archive/20261024-integrate-starrocks-oss/full-artifacts/.gitignore
- aidlc-docs/archive/20261024-integrate-starrocks-oss/full-artifacts/README.md
- aidlc-docs/archive/20261024-integrate-starrocks-oss/full-artifacts/infra
- aidlc-docs/archive/20261024-integrate-starrocks-oss/full-artifacts/scripts

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261024-integrate-starrocks-oss/full-artifacts/`
