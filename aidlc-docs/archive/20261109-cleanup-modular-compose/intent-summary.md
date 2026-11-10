# Intent Summary: Cleanup and Modular Compose

## Intent
Cleanup and Modular Compose (`20261109-cleanup-modular-compose`)

## Objective
Remove files no longer needed (including the TPC-H generator and loader), split Docker Compose into core, jupyter, jenkins, airflow, and starrocks modules, organise scripts by purpose, rewrite the README, and repair the Spark smoke checks.

## Date
2026-11-09

## Scope
Included: removal of 18 unused files and the Jenkins migration; compose.{core,jupyter,jenkins,airflow,starrocks}.yml with JUPYTER/JENKINS/STARROCKS_ENABLED flags; scripts grouped into setup, bootstrap, operations, clients, verify; README rewrite with a Contents index and no old-stack history; Spark smoke and role matrix on the current runtime image; reproducible builds and orphan handling. Excluded: the BI token intent, the Jenkins CI job restore, the Airflow role drift. Extensions off.

## Units / workstreams
File cleanup, Modular Compose and module flags, Script layout, Spark smoke repair, README rewrite, Build and Test fixes

## Major requirements
- Remove unused files: TPC-H generator and loader, identity provisioner, bucket-init, one-time reset, Ranger secrets, deferred inventory, Jupyter example, root Jenkinsfile, Jenkins migration.
- Split Compose into compose.core/jupyter/jenkins/airflow/starrocks.yml with opt-out flags; resource names unchanged.
- Group scripts by purpose, keeping lakehouse.sh, bootstrap-default-product.sh, and aidlc_intent.py at the top.
- Rewrite the README with a Contents index and no old-stack references.

## Architecture and design decisions
- Core always runs; optional modules are selected by JUPYTER_ENABLED, JENKINS_ENABLED, and STARROCKS_ENABLED; Airflow keeps its own commands.
- lakehouse.sh builds the Compose file list in one place; every other script passes its files explicitly.
- The rendered configuration of core plus jupyter plus jenkins is identical to the former docker-compose.yml, so no reset or migration is needed.

## Implementation decisions
- The Spark smoke and role-matrix jobs set rest.auth.type=oauth2, because the shared runtime image defaults catalogs to the broker AuthManager.
- BUILDX_NO_DEFAULT_ATTESTATIONS=1 makes cached builds keep their image ID, so starts do not recreate containers.
- COMPOSE_IGNORE_ORPHANS=true avoids misleading orphan warnings for partial module commands.

## Deviations
- Change requests during Code Generation: the script layout (FR-7) and the README rewrite (FR-6a).
- Build and Test found and fixed two earlier issues: container recreation on every start, and misleading orphan warnings.
- The user verified that DBeaver's StarRocks connection needs only idTokenFile; docs updated.
- lakehouse-product-access.md was updated (planned as RETAIN), for the new script paths.

## Verification
See construction/build-and-test/build-and-test-summary.md. Product bootstrap end to end (Spark smoke in three environments and the StarRocks steps); repeat start and stop/start leave container IDs unchanged; opt-outs work with module containers untouched; verifiers pass (RustFS OIDC and STS, Polaris, the full role matrix including Spark, Airflow DAGs, StarRocks login); Jenkins 8/9 (known missing CI job). Suite 217 passed, 1 skipped, 2 earlier Airflow drift failures.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/jenkins-ci-access.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/starrocks-sql-access.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md

## Superseded decisions
- docker-compose.yml, docker-compose.airflow.yml, docker-compose.starrocks.yml, and docker-compose.deferred.yml replaced by the compose.<module>.yml files.
- The flat scripts/ layout replaced by scripts/{setup,bootstrap,operations,clients,verify}/.
- The Jenkins home migration and remove-legacy-jenkins removed.
- The legacy Spark image local/spark-iceberg:3.5.5_1.8.1-krb5 replaced by local/lakehouse-spark-runtime:3.5.5_1.10.2 for the smoke checks.

## Archived artifacts
- aidlc-docs/archive/20261109-cleanup-modular-compose/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261109-cleanup-modular-compose/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261109-cleanup-modular-compose/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261109-cleanup-modular-compose/full-artifacts/aidlc-docs/current/compaction/20261109-cleanup-modular-compose/manifest.json
- aidlc-docs/archive/20261109-cleanup-modular-compose/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/archive/20261109-cleanup-modular-compose/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/jenkins-ci-access.md
- aidlc-docs/archive/20261109-cleanup-modular-compose/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/starrocks-sql-access.md
- aidlc-docs/archive/20261109-cleanup-modular-compose/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md
- aidlc-docs/archive/20261109-cleanup-modular-compose/full-artifacts/compose.core.yml
- aidlc-docs/archive/20261109-cleanup-modular-compose/full-artifacts/compose.jupyter.yml
- aidlc-docs/archive/20261109-cleanup-modular-compose/full-artifacts/compose.jenkins.yml
- aidlc-docs/archive/20261109-cleanup-modular-compose/full-artifacts/compose.airflow.yml
- aidlc-docs/archive/20261109-cleanup-modular-compose/full-artifacts/compose.starrocks.yml
- aidlc-docs/archive/20261109-cleanup-modular-compose/full-artifacts/scripts
- aidlc-docs/archive/20261109-cleanup-modular-compose/full-artifacts/.env.example
- aidlc-docs/archive/20261109-cleanup-modular-compose/full-artifacts/.gitignore
- aidlc-docs/archive/20261109-cleanup-modular-compose/full-artifacts/README.md
- aidlc-docs/archive/20261109-cleanup-modular-compose/full-artifacts/infra/spark-bootstrap
- aidlc-docs/archive/20261109-cleanup-modular-compose/full-artifacts/tests

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261109-cleanup-modular-compose/full-artifacts/`
