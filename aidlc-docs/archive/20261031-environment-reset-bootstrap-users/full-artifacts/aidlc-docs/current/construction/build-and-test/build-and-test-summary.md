# Build and Test Summary — Environment Reset and Bootstrap Users

Run on 2026-10-31 against the live local stack (`lakehouse-local`). The result passed with one expected Jenkins finding and two items for follow-up.

## Before the reset
A safety backup of the Jenkins home was taken: `.runtime/backups/20261031-pre-reset/jenkins-home.tar.gz`. It is 277 MB, holds 15,244 entries, and has a SHA-256 next to it. The reset does not remove `.runtime/backups`.

## Results

| Check | Result |
|---|---|
| Static checks (bash, py_compile, Compose config) | Pass |
| Contract tests | 184 passed, 1 skipped, 2 pre-existing Airflow drift failures; broker tests 10 passed |
| Reset dry run | 16 containers, 7 volumes, 6 networks, 3 directories; no other project listed |
| Reset `--yes` | Every item removed. A second dry run finds nothing. `.runtime/backups` and the test venv were kept |
| Product bootstrap from nothing | Pass: realm, 5 groups, `lakehouse-writer`, 5 users created, buckets, catalogs, grants; writer check (403 and 401) and Spark smoke tables pass for prod, UAT, and dev |
| User logins (5) | Pass: password grant 200, single correct group, permanent password, no required actions, correct Polaris role (`platform-admin` maps to owner) |
| Rerun of `bootstrap-users.sh` after drift | Pass: joe's password, group, and required action restored; peter's extra group removed; a control user outside the list unchanged, then deleted |
| RustFS OIDC verifier | 7 of 7 pass |
| RustFS STS verifier | Pass |
| Polaris negative cases | Pass (401 for both) |
| Role matrix (temporary users) | Pass: claims and principal roles for all four roles |
| Jenkins verifier | 8 of 9 pass. "migrated workload CI job is missing" is expected after a reset |
| Airflow start | Pass after a fix (below). Bundles cloned into `<infra-v2>/.runtime/airflow-dag-bundles`; main and UAT DAGs registered |
| Broker token | Pass: `srv-default-writer`, `azp=lakehouse-writer`, writer role, 3600 s, renewal works |
| Remove `../opensource-lakehouse/.runtime` | Done: it held only old Bundle clones, was git-ignored, and nothing mounted it. That repository is still clean in git |

## Defect found and fixed during testing
`airflow-init` failed with "Bundle host root must be this repository's ...". The validator image copy compared the host path with its own location inside the container. Before FR-9, `LAKEHOUSE_PROJECT_ROOT` carried that path in.

Fix: the host-root check now runs only with `--host-paths`, which `scripts/lakehouse.sh` passes on the host. The container entry point checks only the Bundle configuration. Two contract tests were added for this.

## Change requested after testing: Keycloak realm administration
At your request, the `role-platform-admin` group now has the built-in `realm-admin` role of the `lakehouse` realm's `realm-management` client. This extends FR-4, which originally covered only the product services.

Live check: platform-admin gets HTTP 200 on the `lakehouse` admin API (users, clients, realm) and 403 on `master`. maria-owner gets 403 on all of them. The admin console is at `http://keycloak.localhost:8080/admin/lakehouse/console/`. Rerunning the bootstrap is idempotent. Contract tests: 185 passed, 1 skipped, plus the 2 known drift failures.

## Findings and follow-ups
1. **Jenkins CI job after a reset.** The workload job is stored only in the Jenkins home, not in configuration as code, so a reset removes it. Options: restore it from the backup, or define the job in CasC (Job DSL) in a later intent.
2. **Legacy containers disappeared.** The stopped `hive-dremio-rustfs-*` (11) and `iceberg-poc-*` (6) containers vanished between about 17:41 and 17:50 UTC.
   - The reset did not remove them: it removed only its printed list of 16 names.
   - No script that ran during this window removes other projects' containers. Rancher Desktop keeps no event history, so the cause is unknown.
   - All of their volumes are intact.
3. **Leftover `write-service-account` references.** They remain only in the deferred `infra/tpch-loader` and `infra/starrocks`, which are out of scope.
4. **Writer client accepts any realm user.** `lakehouse-writer` gives tokens to any `lakehouse` user whose password is known, but only with that user's own roles. Its secret is held by the broker and Spark runtime only.
5. **Earlier follow-ups, still open:** Airflow developer-role drift; JupyterHub broker tests need `PYTHONPATH`; RustFS console v0.1.38.
