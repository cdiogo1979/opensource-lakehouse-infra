# Build and Test Summary — jenkins-keycloak-sso

Run date: 2026-10-31, local Docker Compose stack, host Python 3.14.7.

## Build Status
- **Build**: Success. `local/lakehouse-jenkins:2.580.1` built with exactly 104 plugins; spot-checked `oic-auth 4.731.v4932b_506e767`, `matrix-auth 3.3`, `configuration-as-code 2136.veb_3a_554550b_f`.
- **Secrets**: `jenkins-oidc-client-secret` and `jenkins-break-glass-password` created (0600) with read-only mount copies.
- **Keycloak**: `jenkins` client and `lakehouse-jenkins-groups` mapper created; the rerun reports no changes.
- **Migration**:
  - `iceberg-poc-jenkins-home` was copied into `lakehouse-local_jenkins-home` (448 MB) and verified by file count and content digest; the legacy volume was mounted read-only.
  - The marker reads `migrated:iceberg-poc-jenkins-home 2026-10-31T16:23:13Z`.
  - The `main` and `uat` histories are preserved, and the rerun reports `already initialised`.
- **Service**: `jenkins` healthy about 20 s after start and after restart. No SEVERE log lines. `scripts/lakehouse.sh status` lists it.
- **Static checks**: Compose renders; Python compiles; `bash -n` passes. No formatter or linter is configured.

## Test Execution Summary

### Unit Tests
| Run | Result |
|---|---|
| `tests/jenkins`, `tests/keycloak`, `tests/rustfs` | 90 passed |
| Full suite (`PYTHONPATH=infra/jupyter/hub`, seed 20261031) | **174 passed, 1 skipped, 2 failed** (+10 subtests) |

The 2 failures are the pre-existing Airflow role-mapping drift (`tests/airflow/test_keycloak_sso_contract.py`), which is unrelated and unchanged.

### Integration Tests
| Scenario | Result |
|---|---|
| 1. `verify-jenkins-oidc.py` | **9/9 PASS** |
| 2. Idempotency (realm bootstrap, migration helper) | PASS |
| 3. Restart: configuration as code and plugin override reapplied | PASS (9/9 again) |
| 4. Headless SSO and permission matrix (temporary users, deleted) | **22/23 PASS**: every permission, escape-hatch, and logout check passed; the workload CI build result failed (see below) |
| 5. Regression: RustFS OIDC, Airflow UI, JupyterHub | PASS |
| 6. Interactive login | Pending your confirmation |

Scenario 4 details:
- All five users authenticate as their Keycloak identity.
- **Overall/Read**: owner, developer, and analyst get 200; writer and the no-group user get 403.
- **Administer** (`/manage/`): owner 200; developer and analyst 403.
- **Job/Read**: developer and analyst 200; writer 403.
- **Build**: analyst cannot build (403); developer can (201).
- **Break-glass**: `jenkins-break-glass` signs in through the escape hatch and has Administer.
- **Logout**: redirects to the Keycloak end-session endpoint.

### Workload CI build
- **Results**: `main` build #11 (developer-triggered) and `uat` build #4 both ran the full pipeline on v2: anonymous checkout, venv, compile, lint, flake8, and bandit all passed. Both **failed in the unit-test stage** on one test in the workload repository.
- **The failing test**: `tests/jenkins_deployment/test_airflow_bundle_client.py::test_dag_factory_reuses_spark_container_for_bundle_workloads` expects `dag_name="init_environment"` in `dags/test_environment.py`.
- **Cause**: both branches point to `00b6623` ("rename dag", 2026-10-29), which renamed the DAG without updating that test. 47 of 48 tests passed. The previous migrated builds of both branches (legacy `main` #10, `uat` #3) succeeded on the commit before.
- **Conclusion**: Jenkins correctly detected a genuine regression in `opensource-lakehouse`. That repository is outside this intent's scope, so this verification criterion (Q11: A, a successful workload CI build) is **not met**. **Decision (`ci-build-clarification-questions.md` Q1: A)**: you accepted a verification waiver for this criterion only. The waiver is not a pass. The regression is to be fixed in `opensource-lakehouse` and pushed to GitHub, after which Jenkins rebuilds on its next scan.

### Performance and Security
- Performance: N/A.
- Security: the Security Baseline extension is disabled. Verified anonymous denial, no Docker socket, loopback binding, and that secrets are absent from `docker inspect`. No vulnerability scanning was run.

## Overall Status
- **Build**: Success.
- **Jenkins onboarding and SSO**: Pass (wiring, permissions, break-glass, logout, restart, idempotency, plugin pinning, migration).
- **Waived (user-accepted)**: a successful workload CI build. It is blocked by the `opensource-lakehouse` regression in commit `00b6623`.
- **Open item**: your interactive login.
- **Not done yet (gated)**: legacy removal (`remove-legacy-jenkins --confirm`) runs only after you approve the verified results.
