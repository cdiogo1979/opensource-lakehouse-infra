# Code Generation Plan — jenkins-keycloak-sso

This plan is the single source of truth for Code Generation Part 2. Every step is marked `[x]` in the same interaction it completes (DOC-02).

## Unit Context
- **Unit**: `jenkins-keycloak-sso` (single unit). Traceability is to FR-1–FR-12 and JB-1–JB-19.
- **Workspace root**: `/Users/carlosdiogo/code_repo/opensource-lakehouse-infra-v2`. This is brownfield: files are modified in place.
- **Design inputs**: `construction/jenkins-keycloak-sso/functional-design/` and findings J1–J10.
- **Dependencies**:
  - Keycloak 26.8.1 `lakehouse` realm
  - the pinned Jenkins 2.580.1 base image
  - the legacy volume `iceberg-poc-jenkins-home`, read-only source
  - GitHub, anonymous access
- **Not in this stage**:
  - running services, the migration, or legacy removal (Build and Test and the gated final step)
  - knowledge updates (at closure)
  - deploy documents
  - any edit to `../opensource-lakehouse`

## Steps

### Step 1 — Pinned plugins and image (FR-6, JB-7)
- [x] Create `infra/jenkins/plugins.txt`. It lists the 104 exact `name:version` lines (J1, J2), sorted.
- [x] Modify `infra/jenkins/Dockerfile`:
  - copy `plugins.txt` to `/usr/share/jenkins/ref/plugins.txt`
  - run `jenkins-plugin-cli --plugin-file …` as `jenkins`
  - fail the build if `/usr/share/jenkins/ref/plugins/*.jpi` does not exactly match `plugins.txt`
  - keep the existing Python and tool checks

### Step 2 — Security configuration as code (FR-7–FR-9, FR-11, JB-1–JB-9, JB-17)
- [x] Create `infra/jenkins/casc/jenkins.yaml`:
  - **Security realm**: `oic` with manual endpoints (browser vs. back-channel), the canonical issuer, `clientId: jenkins`, and the client secret as `${readFile:/run/secrets/jenkins_oidc_client_secret}`.
  - **Claim fields**: `preferred_username` / `name` / `email` / `groups`.
  - **Session and URLs**: logout via Keycloak, `postLogoutRedirectUrl`, `rootURLFromRequest: true`.
  - **Properties**: `pkce`, and `escapeHatch` (`jenkins-break-glass`, password via `readFile`).
  - **Authorization**: the `globalMatrix` entries (owner and break-glass Administer; developer and analyst as designed; nothing else).
  - **Core settings**: `numExecutors: 2`, `mode: NORMAL`, `crumbIssuer: standard`, `unclassified.location.url`.

### Step 3 — Protected secrets (FR-7, FR-11, JB-9)
- [x] Modify `scripts/prepare-lakehouse-runtime.py`. Create `jenkins-oidc-client-secret` and `jenkins-break-glass-password` once (hex), and stage both read-only mounts (0644).

### Step 4 — Keycloak `jenkins` client (FR-7, JB-5)
- [x] Modify `infra/keycloak/bootstrap-realm.py`:
  - **Constants**: `JENKINS_CALLBACK_PATH = /securityRealm/finishLogin`, post-logout path `/`, `JENKINS_GROUP_MAPPER_NAME = lakehouse-jenkins-groups`, default port 8090.
  - **Port lookup**: generalize the existing console-port helpers into a shared `host_port(variable, default)` (env → `.env` → default), reused by RustFS and Jenkins.
  - **`jenkins_client_configuration(secret, port)`**: the confidential client with PKCE S256, exact `redirectUris`, and `post.logout.redirect.uris`.
  - **`ensure_jenkins_group_mapper`**: the ID, access, and userinfo `groups` claim mapper.
  - **Port moves**: exact-pair port-move reconciliation for `jenkins`, matching the RustFS rule.
  - **`main`**: add `--jenkins-secret-file` (default `.runtime/credentials/jenkins-oidc-client-secret`). Always ensure the client and mapper, and report `jenkins-client=configured`.
- [x] Modify `infra/keycloak/realm-contract.json` to add the `jenkins` client entry.

### Step 5 — Compose service and inventory (FR-1, FR-4, FR-5)
- [x] Modify `docker-compose.yml`:
  - **Service `jenkins`**:
    - built from `infra/jenkins/Dockerfile` as `local/lakehouse-jenkins:2.580.1`
    - published on `127.0.0.1:${JENKINS_HOST_PORT:-8090}:8080`
    - volume `jenkins-home`; read-only mounts for the YAML and the two secrets
    - environment `CASC_JENKINS_CONFIG`, `PLUGINS_FORCE_UPGRADE=true`, `JAVA_OPTS=-Djenkins.install.runSetupWizard=false`, `JENKINS_HOST_PORT`
    - network `core`; `depends_on: keycloak` healthy; healthcheck on `/login`
    - no Docker socket
  - **Volume** `jenkins-home` with `name: lakehouse-local_jenkins-home`.
- [x] Modify `docker-compose.deferred.yml`: `jenkins: status: implemented-in-main-compose`.
- [x] Modify `.env.example` to add `JENKINS_HOST_PORT=8090`.

### Step 6 — Migration helper (FR-2, JB-10–JB-14)
- [x] Create `scripts/migrate-jenkins-home.py`. It uses only the Docker CLI and throwaway containers from the Jenkins image.
  - **Pure decision**: `decide(target_state, marker, legacy_volume_exists, legacy_running)` returns one of `skip`, `refuse`, `copy`, or `fresh`.
  - **Volume creation**: creates the target with Compose labels when missing.
  - **Copy**: `cp -a` from the read-only source.
  - **Verification**: file count and a content digest of source vs. target, excluding the marker.
  - **Marker**: written last.
  - **Output**: prints only state and outcome.

### Step 7 — Operator wiring (FR-1, FR-10, JB-15, JB-16)
- [x] Modify `scripts/lakehouse.sh`:
  - **`start`**: after the realm bootstrap, build the Jenkins image, run the migration helper, run `up -d jenkins`, and wait for healthy.
  - **Status and stop**: add `jenkins` to `SERVICES` and to `stop`, and print the Jenkins URL in the ready message.
  - **New `remove-legacy-jenkins --confirm`** (JB-15, JB-16):
    - checks the marker `migrated:iceberg-poc-jenkins-home`
    - checks that v2 Jenkins is healthy and the legacy container is not running
    - removes exactly `hive-dremio-rustfs-jenkins-1`, then `iceberg-poc-jenkins-home`
    - never touches `jenkins_home` or any image
    - updates the usage text

### Step 8 — Tests (JB-1–JB-19)
- [x] Create `tests/jenkins/test_plugins_contract.py`:
  - 104 unique pins in exact `name:version` form, sorted
  - includes `oic-auth`, `matrix-auth`, `configuration-as-code`, `workflow-aggregator`, and `git`
  - the Dockerfile installs from and verifies against `plugins.txt`
- [x] Create `tests/jenkins/test_casc_contract.py`:
  - **Realm**: manual endpoints (browser `keycloak.localhost`, back-channel `keycloak:8080`), the issuer, PKCE, the escape hatch, `groupsFieldName`, and the `readFile` secrets.
  - **No inline secrets.**
  - **Matrix**: exactly the designed entries; no anonymous, authenticated, or writer entry.
  - The YAML is parsed with a minimal loader, or text contracts if PyYAML is unavailable.
- [x] Create `tests/keycloak/test_jenkins_client_contract.py`:
  - client and mapper configuration
  - port resolution
  - port-move reconciliation, with other changes refused
  - secret mismatch refusal
  - contract JSON matching the code
  - the RustFS client still behaving the same after the helper generalization
- [x] Create `tests/jenkins/test_compose_jenkins_contract.py`:
  - loopback port, volume name, read-only mounts, no Docker socket, no `group_add`, environment, healthcheck, and `depends_on`
  - `CLIENT_SECRET` and passwords absent from Compose
  - runtime preparation staging the two secrets
  - deferred inventory updated
  - `lakehouse.sh` wiring and the guarded removal command (exact names; no `jenkins_home`)
- [x] Create `tests/jenkins/test_migrate_home.py`:
  - every `decide()` branch: skip on marker, refuse on non-empty without a marker, refuse while legacy is running, copy, and fresh
  - the read-only mount of the source and the marker-written-last ordering (source contract)

### Step 9 — Live verification helper (Build and Test hooks)
- [x] Create `scripts/verify-jenkins-oidc.py`. It runs read-only checks:
  - Jenkins healthy; anonymous access returns 403 or the login redirect
  - the login redirect from both hosts targets Keycloak with `client_id=jenkins`, the exact `finishLogin` callback, and PKCE S256
  - Keycloak accepts both callbacks
  - the plugin set reported by the running Jenkins equals `plugins.txt`, checked via the escape-hatch credential over the API
  - the security realm is `oic`, the job `opensource-lakehouse-dp/opensource-lakehouse-ci` exists, and the home marker is present
  - no secret appears in `docker inspect`

### Step 10 — Documentation (FR-12)
- [x] Modify `README.md`:
  - a "Jenkins CI and Keycloak SSO" section covering URL, start/stop, permissions table, break-glass, migration behavior, legacy removal, rotation, and verification
  - replace the "Jenkins deferred" statement
- [x] Create `aidlc-docs/current/construction/jenkins-keycloak-sso/code/code-summary.md`.

## Traceability
| Requirement | Steps |
|---|---|
| FR-1 Jenkins in v2 | 5, 7 |
| FR-2 Migrated home | 6, 7 |
| FR-3 Jobs | 6 (migrated job), 9 |
| FR-4 Execution model | 2 (executors), 5 (no socket) |
| FR-5 GitHub access | migrated job config (unchanged); 9 |
| FR-6 Pinned plugins | 1, 5 (`PLUGINS_FORCE_UPGRADE`) |
| FR-7 Keycloak SSO | 2, 3, 4 |
| FR-8 Authorization | 2, 8 |
| FR-9 Configuration as code | 2, 5 |
| FR-10 Legacy removal | 7 (command only; executed after approval) |
| FR-11 Break-glass | 2, 3 |
| FR-12 Docs and knowledge | 10 (knowledge at closure) |

## Scope
10 steps:
- created: 13 files (plus the code summary)
- modified: 8 files
- deleted: none
