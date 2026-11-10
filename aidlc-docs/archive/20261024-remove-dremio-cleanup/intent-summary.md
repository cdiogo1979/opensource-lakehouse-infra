# Intent Summary: Remove Dremio and Clean the Project

## Intent
Remove Dremio and Clean the Project (`20261024-remove-dremio-cleanup`)

## Objective
Remove Dremio from the active local lakehouse project, retain the Hive/RustFS/Spark/Jupyter platform, and organize retained tooling while preserving user data.

## Date
2026-10-24

## Scope
Remove Dremio Compose, identity/configuration, JDBC integration, and stale examples; retain the TPCH Spark ETL and existing platform/data. Move Spark, loader, and generator files into infra/. Remove duplicate root TPCH input files only after byte-comparison with retained runtime copies. Runtime Dremio cleanup and live service/ETL checks were not performed.

## Units / workstreams
Unit 1 — Dremio removal and retained lakehouse cleanup

## Major requirements
- Remove Dremio and its JDBC integration from the active local project.
- Retain Hive Metastore, PostgreSQL, Kerberos, RustFS, Spark, JupyterHub, and the TPCH Spark ETL.
- Preserve non-Dremio platform data, identities, credentials, volumes, and notebook workspaces.
- Remove only Dremio-specific runtime state through a narrowly scoped, confirmation-gated operation.

## Architecture and design decisions
- Keep Hive Metastore as the Iceberg catalog and RustFS as table storage; do not introduce a replacement query engine.
- Keep TPCH ETL writing as write-service-account and separate runtime cleanup from source/configuration cleanup.
- Place Spark configuration, TPCH loader code, and TPCH generator assets under infra/.
- Preserve the previous intent archive as historical evidence.

## Implementation decisions
- Removed active Dremio service, identity/proxy configuration, JDBC workload integration, and stale Dremio SQL examples.
- Updated Compose paths for infra/spark, infra/tpch-loader, and infra/tpch-generator.
- Removed the standalone obsolete Hadoop Catalog seed example and duplicate root TPCH data after exact byte comparison with retained .runtime/workload/tpch-data/ files.
- Added or retained a confirmation-gated Dremio-only cleanup script; it was not executed.

## Deviations
- Live integration and runtime cleanup were not performed. The user accepted this verification limitation; these checks remain unverified.
- The private .env and ignored .runtime data/credentials were excluded from the archive inventory to avoid capturing local settings and secrets.
- No Git metadata exists in the project directory, so the handoff has no repository diff or branch.

## Verification
The user explicitly accepted option B in deploy/verification-closure-questions.md on 2026-10-24. Docker Compose image builds, Compose configuration parsing, shell syntax, Python syntax, and targeted path/reference checks passed. Live service health and catalog/ETL integration were not run. The legacy Dremio container/data volume, KDC principal, and local Dremio credentials/keytab were not removed. No containers were started or stopped. This is an accepted verification limitation, not a pass.

## Canonical documents updated
- aidlc-docs/knowledge/hive-dremio-rustfs/application-design.md
- aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/lakehouse-workload-and-access.md

## Superseded decisions
- None recorded

## Archived artifacts
- aidlc-docs/archive/20261024-remove-dremio-cleanup/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261024-remove-dremio-cleanup/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261024-remove-dremio-cleanup/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261024-remove-dremio-cleanup/full-artifacts/aidlc-docs/current/compaction/20261024-remove-dremio-cleanup/manifest.json
- aidlc-docs/archive/20261024-remove-dremio-cleanup/full-artifacts/aidlc-docs/knowledge/hive-dremio-rustfs
- aidlc-docs/archive/20261024-remove-dremio-cleanup/full-artifacts/docker-compose.yml
- aidlc-docs/archive/20261024-remove-dremio-cleanup/full-artifacts/.env.example
- aidlc-docs/archive/20261024-remove-dremio-cleanup/full-artifacts/.gitignore
- aidlc-docs/archive/20261024-remove-dremio-cleanup/full-artifacts/README.md
- aidlc-docs/archive/20261024-remove-dremio-cleanup/full-artifacts/infra/hive
- aidlc-docs/archive/20261024-remove-dremio-cleanup/full-artifacts/infra/kerberos
- aidlc-docs/archive/20261024-remove-dremio-cleanup/full-artifacts/infra/identity-provisioner
- aidlc-docs/archive/20261024-remove-dremio-cleanup/full-artifacts/infra/spark
- aidlc-docs/archive/20261024-remove-dremio-cleanup/full-artifacts/infra/tpch-loader
- aidlc-docs/archive/20261024-remove-dremio-cleanup/full-artifacts/infra/tpch-generator
- aidlc-docs/archive/20261024-remove-dremio-cleanup/full-artifacts/scripts

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261024-remove-dremio-cleanup/full-artifacts/`
