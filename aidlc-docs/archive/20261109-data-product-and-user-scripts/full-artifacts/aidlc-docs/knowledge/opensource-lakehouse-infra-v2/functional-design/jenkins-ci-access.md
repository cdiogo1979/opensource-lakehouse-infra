# Functional Design — Jenkins CI and Access

Current functional design of the v2 Jenkins component. For architecture, see [`../application-design.md`](../application-design.md). History is in the [Jenkins Onboarding and Keycloak SSO intent archive](../../../archive/20261031-jenkins-keycloak-sso/intent-summary.md).

## Responsibility
Jenkins runs the CI for the `opensource-lakehouse` workload repository through the multibranch pipeline `opensource-lakehouse-dp/opensource-lakehouse-ci`. It scans `https://github.com/cdiogo1979/opensource-lakehouse/` anonymously on its schedule and runs that repository's `Jenkinsfile` (venv, compile, lint, flake8, bandit, pytest) on the built-in node with 2 executors. It has no Docker socket and no webhooks. There is no job for this infrastructure repository.

## Access rules
| Keycloak group / identity | Jenkins permissions |
|---|---|
| `role-default-owner` | `Overall/Administer` |
| `role-platform-admin` | `Overall/Administer` |
| `jenkins-break-glass` (escape hatch) | `Overall/Administer` |
| `role-default-developer` | `Overall/Read`, `Job/Read`, `Job/Build`, `Job/Cancel`, `Job/Workspace` |
| `role-default-analyst` | `Overall/Read`, `Job/Read` |
| `role-default-writer`, users without a group, anonymous | none |

- **Authorities**: group names arrive as plain values of the ID-token `groups` claim. A user in several groups receives the union of their permissions.
- **Sign-in**: people sign in through the Keycloak `jenkins` client only. The legacy local user database remains in the home but is not a login path.
- **Escape hatch**: the `jenkins-break-glass` login uses a protected password file. The plugin stores it BCrypt-hashed. It keeps working when Keycloak is unavailable.

## Configuration authority
- **Plugins**: `infra/jenkins/plugins.txt` (104 exact versions) is the plugin source of truth. The image overrides the home's plugins at start, and there are no runtime installs.
- **Security as code**: `infra/jenkins/casc/jenkins.yaml` owns the security realm, authorization matrix, escape hatch, executors, mode, crumb issuer, and root URL. It is reapplied at every start, so UI changes to these are overwritten. Jobs and build history are migrated state, not code.
- **Secrets**: the client secret and the break-glass password come from mounted files. Nothing secret is written to configuration as code, Compose, or the container environment.

## Home
- **Location**: Jenkins runs from `compose.jenkins.yml` (unless `JENKINS_ENABLED=false`) with its home in the named volume `lakehouse-local_jenkins-home`.
- **New home**: a new volume is filled from the image, owned by the `jenkins` user, so Jenkins starts with an empty home.
- **Jobs**: jobs and build history live only in the home and are not configuration as code.
- **Migration removed**: the one-time copy from the pre-v2 Jenkins and the guarded legacy removal were completed in October 2026 and removed on 2026-11-09. They are preserved in the intent archives.

## Failure behavior
- **Keycloak unavailable**: SSO logins fail, the escape hatch works, and builds continue.
- **Plugin mismatch at image build**: the build fails.

## Verification and known limits
- Verified 2026-10-31:
  - the permission matrix for every group, plus refusal of users without a group
  - escape hatch and logout
  - plugin parity
  - restart and idempotency
  - an interactive login
- **Waived**: a successful workload CI build. The `opensource-lakehouse` commit `00b6623` broke one unit test, so `main` #11 and `uat` #4 fail at pytest after all other stages pass.
- Pipelines needing Docker are not supported.
- **Reset (2026-10-31)**: `scripts/lakehouse.sh reset` deletes `lakehouse-local_jenkins-home`, including jobs and build history, because jobs are not configuration as code.
  - After the reset, Jenkins started with no workload job.
  - The pre-reset home is saved at `.runtime/backups/20261031-pre-reset/jenkins-home.tar.gz` (SHA-256 alongside).
  - Open: restore the job, or define it as code, for example with Job DSL in CasC.
- Back up `lakehouse-local_jenkins-home` before any reset.
