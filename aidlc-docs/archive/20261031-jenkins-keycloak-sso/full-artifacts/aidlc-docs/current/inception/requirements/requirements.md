# Requirements — Jenkins Onboarding and Keycloak SSO

## Intent Analysis
- **User request**: "go ahead and start a new aidlc to onboard jenkins (and integrate sso)"
- **Request type**: Migration plus New Feature. The legacy Jenkins moves into the v2 stack, and Keycloak SSO is added.
- **Scope estimate**: Multiple Components:
  - Jenkins image and plugins
  - Compose service and volume
  - one-time home migration
  - configuration as code
  - Keycloak realm bootstrap and contract
  - protected credentials
  - operator entry points
  - legacy cleanup
  - tests and documentation
- **Complexity estimate**: Moderate to complex. Migrating a hand-configured home requires pinning 102 plugins and preserving the existing job and history. The OIDC plugin version must be compatible with the pinned Jenkins 2.580.1 LTS.
- **Requirements depth**: Standard
- **Clarifications**: `requirement-verification-questions.md` (14 answers) and `requirement-verification-clarification-questions.md` (3 answers). Ambiguities resolved; no remaining contradictions.

## Functional Requirements

### FR-1 Jenkins in the v2 stack
Jenkins runs as a v2 Compose service, started by the core `scripts/lakehouse.sh start` (Q10: B). It is built from `infra/jenkins/Dockerfile`, which stays on the pinned Jenkins 2.580.1 LTS base, matching the migrated home. It is published only on `127.0.0.1:${JENKINS_HOST_PORT:-8090}` (Q6: A). `docker-compose.deferred.yml` no longer lists it as deferred, and `status`/`stop` include it.

### FR-2 Migrated home (Q1: B, C1: A)
- **Copy**: the legacy `iceberg-poc-jenkins-home` is copied once into a new volume, `lakehouse-local_jenkins-home`. The copy is idempotent and refuses to overwrite a non-empty target.
- **Legacy volume**: stays untouched as a backup until the approved removal (FR-10).
- **Preserved**: the existing `opensource-lakehouse-dp/opensource-lakehouse-ci` multibranch job and its build history.

### FR-3 Jobs (Q2: A)
The only job is the workload CI: the migrated multibranch pipeline for `https://github.com/cdiogo1979/opensource-lakehouse/`, running its `Jenkinsfile`. No job is added for this infrastructure repository.

### FR-4 Execution model (Q3: A)
Pipelines run on built-in-node executors inside the Jenkins container. The Docker socket is not mounted. The image provides Python 3.10, bash, and git.

### FR-5 GitHub access (Q8: A)
Anonymous HTTPS, with periodic multibranch scanning (polling) for discovery. No webhooks and no GitHub credentials.

### FR-6 Pinned plugins (Q7: A, C2: A)
- **Source of truth**: an exact-version `plugins.txt` installed at image build pins exactly the legacy plugin versions, plus the OIDC plugin (`oic-auth`) and its required dependencies.
- **Image is authoritative**: it overrides plugin copies in the migrated home at start.
- **No runtime changes**: no plugins are installed or updated at runtime.

### FR-7 Keycloak SSO
- **Client**: browser login through a dedicated confidential Keycloak client in the `lakehouse` realm, using the OIDC Authorization Code flow.
- **Bootstrap**: the client is created by `infra/keycloak/bootstrap-realm.py` and declared in `realm-contract.json`.
- **URIs**: exact callback and post-logout URIs for `localhost` and `127.0.0.1` on the Jenkins port. The fail-closed bootstrap pattern applies.
- **Groups**: a `groups` claim with plain group names.

### FR-8 Group-based authorization (Q4: A)
Jenkins permissions come from the `groups` claim:

| Keycloak group | Jenkins permissions |
|---|---|
| `role-default-owner` | Administer |
| `role-default-developer` | Overall/Read, Job/Read, Job/Build, Job/Cancel, Job/Workspace (view logs and artifacts) |
| `role-default-analyst` | Overall/Read, Job/Read (read-only) |
| `role-default-writer` | No Jenkins access |

Users without an approved group get no access. Anonymous users have no access.

### FR-9 Security configured as code (C3: A)
Configuration as code manages the security realm, authorization matrix, escape-hatch admin, and Jenkins root URL. It is applied at every start, so it is reproducible. Migrated jobs, build history, and other settings remain as migrated.

### FR-10 Legacy removal (Q9: B)
After the v2 Jenkins is verified and you approve it, remove the legacy container `hive-dremio-rustfs-jenkins-1` and the volume `iceberg-poc-jenkins-home`. The unrelated `jenkins_home` volume (from the `jenkins-docker` project) is not touched. The removal is a separate, explicit operator step, never automatic.

### FR-11 Break-glass (Q5: A)
The OIDC plugin's escape-hatch local admin is enabled. Its credentials come from a protected runtime secret file, and it is documented like the Airflow and RustFS break-glass paths. The legacy local user database is not used for login.

### FR-12 Documentation and knowledge
- **Docs**: update `README.md` with Jenkins start/stop, SSO, the permission table, break-glass, migration, legacy removal, and secret rotation.
- **Knowledge at closure**: UPDATE `knowledge/opensource-lakehouse-infra-v2/application-design.md`. Per-component functional design follows the Workflow Planning inventory.

## Out of Scope
- A job for this infrastructure repository.
- Docker or remote agents.
- GitHub webhooks or tokens.
- Changes to `opensource-lakehouse/Jenkinsfile`.
- Jenkins API-token or CLI SSO.
- MFA.
- Non-loopback exposure.
- Jenkins version upgrades.

## Non-Functional Requirements
- **Security** (project conventions; the Security Baseline extension is not enabled):
  - loopback only, no Docker socket
  - secrets only as protected files, with nothing secret in Compose, logs, or configuration as code
  - exact callbacks
  - anonymous access disabled
- **Reproducibility**: pinned base image and exact plugin versions. Security configuration is fully rebuilt from code at start.
- **Data safety**: the migration copies rather than moves data. The legacy backup is kept until a verified, approved removal.
- **Availability**: if Keycloak is unavailable, SSO logins fail and the escape hatch still works. Running builds are unaffected.

## Verification Requirements (Q11: A)
- Automated contract tests: Compose, plugins, configuration as code, Keycloak client, and migration script.
- Local runtime checks: Jenkins healthy, the OIDC redirect uses exact callbacks, configuration as code is applied, and the job and history are present.
- A headless OIDC login and permission check with temporary users, one per approved group, plus a no-group user.
- A successful workload CI build of `opensource-lakehouse` (for example on `main`).
- An interactive login confirmed by you.

## Assumptions and Risks

> **Update 2026-10-31 (Functional Design findings J1–J10)**:
> - Risk 1 is resolved: `oic-auth 4.731.v4932b_506e767` resolves with all 102 legacy pins unchanged and adds only `nimbus-jose-jwt-api`.
> - Risk 2 is resolved: manual endpoints route the back-channel through `keycloak:8080`, so no alias is needed.
> - Risk 3 is resolved by design: `groupsFieldName: groups` with matrix group entries. It is verified at runtime in Build and Test.
> - Risks 4 to 6 are unchanged.
1. **OIDC plugin compatibility**: an `oic-auth` version compatible with Jenkins 2.580.1 and the pinned plugin set must exist. It may require dependency versions that differ from the legacy pins. Resolution happens in design. Any deviation from exact legacy versions returns for approval.
2. **Hostname**: Keycloak advertises `keycloak.localhost`, which resolves to loopback inside containers. The plugin's manual endpoint configuration should avoid a network alias; this is verified in design.
3. **Groups-to-authority mapping**: Jenkins must receive group names exactly as the `groups` claim provides them. The matrix authorization configuration must reference them; verified in design.
4. **Legacy jobs and the CI build**: the migrated job ran with the Docker socket before. If any `opensource-lakehouse` pipeline step needs Docker, FR-4 would block it. The current `Jenkinsfile` uses only `sh` with Python.
5. **Startup cost**: always starting Jenkins in core start adds startup time and memory to every core start.
6. **Legacy ownership**: the legacy container belongs to the sibling `hive-dremio-rustfs` Compose project. Removing it affects that project's stack.

## Extension Configuration
| Extension | Decision |
|---|---|
| Security Baseline | No (Q12: B) |
| Property-Based Testing | No (Q13: C) |
| Resiliency Baseline | No (Q14: B) |
