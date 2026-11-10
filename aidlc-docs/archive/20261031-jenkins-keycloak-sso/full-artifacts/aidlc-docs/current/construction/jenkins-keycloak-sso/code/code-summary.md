# Code Summary — jenkins-keycloak-sso

Generated per `aidlc-docs/current/construction/plans/jenkins-keycloak-sso-code-generation-plan.md` (Steps 1–10).

## Created
| File | Purpose | Traceability |
|---|---|---|
| `infra/jenkins/plugins.txt` | 104 exact plugin pins: the 102 legacy versions plus `oic-auth 4.731.v4932b_506e767` and `nimbus-jose-jwt-api`. | FR-6, JB-7 |
| `infra/jenkins/casc/jenkins.yaml` | Security as code: OIDC realm with manual endpoints, PKCE, escape hatch, `readFile` secrets, global matrix, executors, mode, crumb issuer, root URL. | FR-7–FR-9, FR-11, JB-1–JB-9, JB-17 |
| `scripts/migrate-jenkins-home.py` | One-time verified copy of the legacy home. Its decision table (`skip`, `refuse-unmarked`, `refuse-legacy-running`, `copy`, `fresh`) means it never overwrites a home; it writes the marker last. | FR-2, JB-10–JB-14 |
| `scripts/verify-jenkins-oidc.py` | Read-only live checks for Build and Test. | Verification hooks |
| `tests/jenkins/test_plugins_contract.py` | Plugin pin and Dockerfile contracts. | FR-6 |
| `tests/jenkins/test_casc_contract.py` | Endpoint, claim, secret, escape-hatch, and exact-matrix contracts. | JB-1–JB-9 |
| `tests/jenkins/test_compose_jenkins_contract.py` | Compose, secrets, deferred inventory, start ordering, and guarded removal. | FR-1, FR-4, FR-10, JB-15, JB-16 |
| `tests/jenkins/test_migrate_home.py` | Migration decision table and copy-safety contracts. | JB-10–JB-14 |
| `tests/keycloak/test_jenkins_client_contract.py` | Jenkins client, mapper, port, reconciliation, refusal, and contract JSON. | FR-7, JB-5 |

## Modified
| File | Change | Traceability |
|---|---|---|
| `infra/jenkins/Dockerfile` | Installs `plugins.txt` with `jenkins-plugin-cli` and fails the build if the installed set differs. | FR-6 |
| `infra/keycloak/bootstrap-realm.py` | `jenkins` client and `lakehouse-jenkins-groups` mapper. Shared `host_port`, `loopback_uris`, and loopback port-move helpers; the RustFS wrappers keep their names. Shared ID-token group mapper. `--jenkins-secret-file`. | FR-7, JB-5 |
| `infra/keycloak/realm-contract.json` | Declares the `jenkins` client. | FR-7 |
| `scripts/prepare-lakehouse-runtime.py` | Creates and stages `jenkins-oidc-client-secret` and `jenkins-break-glass-password`. | FR-7, FR-11 |
| `docker-compose.yml` | `jenkins` service (loopback 8090, no Docker socket, read-only configuration and secret mounts, healthcheck) and the `lakehouse-local_jenkins-home` volume. | FR-1, FR-4 |
| `docker-compose.deferred.yml`, `.env.example` | Jenkins marked as implemented; `JENKINS_HOST_PORT=8090`. | FR-1 |
| `scripts/lakehouse.sh` | Core start builds, migrates, starts, and waits for Jenkins. `status` and `stop` include it. New guarded `remove-legacy-jenkins --confirm`. | FR-1, FR-2, FR-10 |
| `README.md` | Jenkins endpoint, the "Jenkins CI and Keycloak SSO" section, and the updated deferred-integrations text. | FR-12 |

## Generation-time checks
- The core Compose config renders.
- Python compiles and `bash -n` passes.
- `remove-legacy-jenkins` without `--confirm` refuses (exit 2).
- `tests/jenkins`, `tests/keycloak`, and `tests/rustfs`: 90 passed.
- The image build, migration, live checks, and the CI build belong to Build and Test.

## Notes
- No service, volume, realm, or credential was changed during generation, and nothing in `../opensource-lakehouse` was edited.
