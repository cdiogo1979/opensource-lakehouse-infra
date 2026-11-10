# Intent Summary: Environment Reset and Bootstrap Users

## Intent
Environment Reset and Bootstrap Users (`20261031-environment-reset-bootstrap-users`)

## Objective
A full local environment reset; a tested two-step start that creates five default users with a permanent password; the writer workload moved to srv-default-writer; Airflow Bundles owned by this repository; README start and reset documentation.

## Date
2026-10-31

## Scope
Included: reset script and command, bootstrap users and on-demand enforcement, role-platform-admin across Polaris/RustFS/Airflow/Jenkins and (by later request) Keycloak lakehouse realm-admin and JupyterHub admin, writer migration from write-service-account to srv-default-writer via lakehouse-writer, Bundles moved into infra-v2 with LAKEHOUSE_PROJECT_ROOT removed, one-time removal of ../opensource-lakehouse/.runtime, README. Excluded: deferred tpch-loader and starrocks, Airflow developer-role drift, Jenkins job as code, extensions (security, PBT, resiliency) off.

## Units / workstreams
Reset script and command, Bootstrap users, platform-admin group, and enforcement, Writer identity migration, Airflow Bundles inside infra-v2, README, tests, Build and Test, and Deploy handoff

## Major requirements
- scripts/lakehouse.sh reset deletes all lakehouse-local containers, data volumes, Jupyter homes, networks, and three generated .runtime directories, with a typed confirmation, --yes, and --dry-run.
- Five bootstrap users (joe-developer, peter-analyst, maria-owner, srv-default-writer, platform-admin) with the permanent password ChangeM3!, created only when missing at start and reset to defaults by scripts/bootstrap-users.sh.
- role-platform-admin is owner-equivalent in Polaris, RustFS, Airflow, and Jenkins; by later user request also lakehouse realm-admin in Keycloak and JupyterHub admin.
- Airflow and Spark write as srv-default-writer through the lakehouse-writer client; Airflow Bundles live in this repository; README documents start and reset.

## Architecture and design decisions
- Reset selects resources by Compose project label, runtime-role label, exact volume and network names, and the lakehouse-jupyter-home- prefix; a path guard limits file deletion to three .runtime directories.
- A single file, infra/keycloak/bootstrap-users.json, is the source for users, groups, and the default password; start never changes existing users.
- platform-admin is in role-platform-admin only, which maps to the existing owner Polaris role and an identical RustFS policy instead of a new Polaris role.
- The two repositories are independent: only Airflow's Git clone of Bundles links them.

## Implementation decisions
- New confidential client lakehouse-writer: password grant only, 3600 s tokens, Polaris role mapper; the writer password file is written from the JSON by prepare-lakehouse-runtime.py.
- The Bundle validator checks the host root only with --host-paths (host); the copy inside the image checks only the Bundle configuration.
- grant_realm_admin gives role-platform-admin the realm-management realm-admin role of the lakehouse realm; JupyterHub allowed_groups and admin_groups include role-platform-admin.

## Deviations
- Build and Test found an airflow-init failure caused by removing LAKEHOUSE_PROJECT_ROOT; fixed with the --host-paths flag and two tests.
- Keycloak realm-admin and JupyterHub admin for role-platform-admin were added during Build and Test at the user's request (FR-4 change notes).
- A Jenkins home backup was taken before the reset; the reset removed the Jenkins CI job, which was not restored.

## Verification
See construction/build-and-test/build-and-test-summary.md. Live reset (16 containers, 7 volumes, 6 networks, 3 directories) and rebuild from nothing passed; product bootstrap and Spark smoke tables (prod, UAT, dev); five user logins with correct groups, permanent passwords, and Polaris roles; bootstrap-users.sh re-enforcement after drift with an unlisted user untouched; RustFS OIDC 7/7 and STS; Polaris negative cases; role matrix; Airflow start with Bundles in infra-v2 and broker token as srv-default-writer; platform-admin lakehouse realm admin (200) and master denied (403); JupyterHub login confirmed by the user. Jenkins verifier 8/9: the CI job is absent after the reset, an expected effect recorded as a follow-up. Contract tests 185 passed, 1 skipped, 2 pre-existing Airflow drift failures. Not run: verify-keycloak-outage.py.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/jenkins-ci-access.md

## Superseded decisions
- write-service-account (client credentials) replaced by srv-default-writer through lakehouse-writer (password grant).
- The platform-admin user with a generated one-time password in the owner group replaced by platform-admin with ChangeM3! in role-platform-admin; .runtime/credentials/platform-admin-password retired.
- Airflow Bundles at ../opensource-lakehouse/.runtime/airflow-dag-bundles with LAKEHOUSE_PROJECT_ROOT replaced by <infra-v2>/.runtime/airflow-dag-bundles; knowledge/opensource-lakehouse retired.
- The Jenkins home as a verified copy of the legacy home replaced by a fresh home after the reset (backup kept).

## Archived artifacts
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/aidlc-docs/current/compaction/20261031-environment-reset-bootstrap-users/manifest.json
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/jenkins-ci-access.md
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/scripts/reset-lakehouse.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/scripts/lakehouse.sh
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/scripts/bootstrap-users.sh
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/scripts/bootstrap-default-product.sh
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/scripts/prepare-lakehouse-runtime.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/scripts/provision-airflow-secrets.sh
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/scripts/run-bootstrap-smoke-spark.sh
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/scripts/verify-polaris-keycloak-auth.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/scripts/verify-keycloak-outage.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/scripts/verify-polaris-oidc-negative-cases.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/infra/keycloak/bootstrap-users.json
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/infra/keycloak/bootstrap-users.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/infra/keycloak/bootstrap-realm.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/infra/keycloak/realm-contract.json
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/infra/polaris/reconcile-keycloak-groups.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/infra/rustfs/bootstrap-policies.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/infra/airflow/airflow_sso_roles.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/infra/airflow/webserver_config.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/infra/airflow/validate-bundle-config.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/infra/jenkins/casc/jenkins.yaml
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/infra/jupyter/hub/lakehouse_policy.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/infra/jupyter/hub/jupyterhub_config.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/infra/airflow-token-broker/app.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/infra/spark-bootstrap/create_smoke_tables.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/docker-compose.airflow.yml
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/README.md
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/tests/keycloak/test_bootstrap_users_contract.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/tests/operations
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/tests/airflow/test_bundle_root_contract.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/tests/airflow/test_keycloak_sso_contract.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/tests/rustfs/test_policy_contract.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/tests/jenkins/test_casc_contract.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/tests/jupyterhub/test_config_contract.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/tests/jupyterhub/test_lakehouse_policy.py
- aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/tests/integration/test_unit4_hub_journey_contract.py

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261031-environment-reset-bootstrap-users/full-artifacts/`
