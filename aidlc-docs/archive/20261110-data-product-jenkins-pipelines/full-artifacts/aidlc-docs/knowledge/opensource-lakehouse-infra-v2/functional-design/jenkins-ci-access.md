# Functional Design — Jenkins CI and Access

Current functional design of the v2 Jenkins component. For architecture, see [`../application-design.md`](../application-design.md). History is in the [Jenkins Onboarding and Keycloak SSO intent archive](../../../archive/20261031-jenkins-keycloak-sso/intent-summary.md) and the [Data Product and User Scripts intent archive](../../../archive/20261109-data-product-and-user-scripts/intent-summary.md).

## Responsibility
Jenkins runs the CI for the `opensource-lakehouse` workload repository through the multibranch pipeline `opensource-lakehouse-dp/opensource-lakehouse-ci`. It scans `https://github.com/cdiogo1979/opensource-lakehouse/` anonymously on its schedule and runs that repository's `Jenkinsfile` (venv, compile, lint, flake8, bandit, pytest) on the built-in node with 2 executors. It has no Docker socket and no webhooks. There is no job for this infrastructure repository.

## Access rules
The matrix has two static entries and one entry per product role listed in that product's `apps.jenkins` (`data-products/<name>.yaml`). Jenkins has no per-product permissions, so a product's rights apply to the whole Jenkins.

| Keycloak group / identity | Jenkins permissions | Source |
|---|---|---|
| `role-platform-admin` | `Overall/Administer` | static |
| `jenkins-break-glass` (escape hatch) | `Overall/Administer` | static |
| `role-default-owner` | `Overall/Administer` | `default.yaml` (the template default for every product's owner) |
| `role-default-developer` | `Overall/Read`, `Job/Read`, `Job/Build`, `Job/Cancel`, `Job/Workspace` | `default.yaml` |
| `role-default-analyst` | `Overall/Read`, `Job/Read` | `default.yaml` |
| writer groups, users without a group, anonymous | none | |

- **Allowed permissions** in a product file: `Overall/Administer`, `Overall/Read`, `Job/Read`, `Job/Build`, `Job/Cancel`, `Job/Workspace`, `Job/Configure`, `Job/Create`, `Job/Delete`, `View/Read`. A product group may not reuse a static entry's name.

- **Authorities**: group names arrive as plain values of the ID-token `groups` claim. A user in several groups receives the union of their permissions.
- **Sign-in**: people sign in through the Keycloak `jenkins` client only. The legacy local user database remains in the home but is not a login path.
- **Escape hatch**: the `jenkins-break-glass` login uses a protected password file. The plugin stores it BCrypt-hashed. It keeps working when Keycloak is unavailable.

## Configuration authority
- **Plugins**: `infra/jenkins/plugins.txt` (104 exact versions) is the plugin source of truth. The image overrides the home's plugins at start, and there are no runtime installs.
- **Security as code**: `infra/jenkins/casc/jenkins.yaml` is the template for the security realm, the static matrix entries, the escape hatch, executors, mode, crumb issuer, and root URL.
  - `infra/products/render_jenkins.py` adds the product entries deterministically and writes `.runtime/container-mounts/jenkins-casc.yaml`, which Compose mounts as `/var/jenkins_casc/jenkins.yaml`. Jenkins reapplies it at every start, so UI changes to these are overwritten.
  - **When it renders**: on every `lakehouse.sh start` (through `prepare-runtime.py`), and on every product apply or removal. Jenkins restarts only when the output changed (`--no-restart` prints the command instead).
  - **In place**: the file is rewritten in place, because a single-file bind mount keeps its inode.
  - **Invalid product files**: the render refuses, and the running Jenkins keeps its last file.
- **Jobs**: jobs and build history are migrated state, not code.
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
- **Verified 2026-11-09** (Data Product and User Scripts): the rendered matrix for `default` equals the former static matrix. A new product's groups appear in the live `config.xml` after the automatic restart and disappear after its removal. `jenkins-oidc.py` passes all checks except the missing workload CI job.
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
