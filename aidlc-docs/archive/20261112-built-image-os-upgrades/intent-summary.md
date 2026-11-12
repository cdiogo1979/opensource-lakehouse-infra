# Intent Summary: Built Image OS Upgrades

## Intent
Built Image OS Upgrades (`20261112-built-image-os-upgrades`)

## Objective
Upgrade OS packages at build in the images built here that took their base's packages as published.

## Date
2026-11-12

## Scope
Included: Airflow, Jenkins, token broker, reconciler, LDAP Dockerfiles; guard test; docs. Excluded: Python and Java packages in those images, external images, Spark-bundled jars.

## Units / workstreams
supply-chain

## Major requirements
- FR-1 apt-get upgrade in Debian images.
- FR-2 apk upgrade in Alpine images.
- FR-3 guard test for every built image.
- FR-4 services still work.
- FR-5 docs.

## Architecture and design decisions
- Follow the base's distribution release; reproducibility between days traded for released fixes, as for Spark and Jupyter.

## Implementation decisions
- Upgrade before the image's own installs, as root, users unchanged.

## Deviations
- Requirements and stages accepted in advance by the user (recommended decisions); push approved separately.

## Verification
construction/build-and-test/build-and-test-summary.md: 664 passed, 3 skipped; fixable OS findings 0 in all five; live restart, jenkins-oidc, role-matrix, UAT DAG run passed; workflow run checked after the push.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md

## Superseded decisions
- None recorded

## Archived artifacts
- aidlc-docs/archive/20261112-built-image-os-upgrades/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261112-built-image-os-upgrades/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261112-built-image-os-upgrades/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261112-built-image-os-upgrades/full-artifacts/infra/airflow/Dockerfile
- aidlc-docs/archive/20261112-built-image-os-upgrades/full-artifacts/infra/jenkins/Dockerfile
- aidlc-docs/archive/20261112-built-image-os-upgrades/full-artifacts/infra/airflow-token-broker/Dockerfile
- aidlc-docs/archive/20261112-built-image-os-upgrades/full-artifacts/infra/polaris/reconciler/Dockerfile
- aidlc-docs/archive/20261112-built-image-os-upgrades/full-artifacts/infra/ldap/Dockerfile
- aidlc-docs/archive/20261112-built-image-os-upgrades/full-artifacts/tests/operations/test_vulnerability_scan.py
- aidlc-docs/archive/20261112-built-image-os-upgrades/full-artifacts/docs/reference/vulnerability-alerts.md
- aidlc-docs/archive/20261112-built-image-os-upgrades/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261112-built-image-os-upgrades/full-artifacts/`
