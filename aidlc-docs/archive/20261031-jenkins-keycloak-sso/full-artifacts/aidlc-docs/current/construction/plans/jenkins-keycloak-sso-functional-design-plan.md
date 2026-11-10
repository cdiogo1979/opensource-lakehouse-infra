# Functional Design Plan — jenkins-keycloak-sso

## Context
- Requirements: `aidlc-docs/current/inception/requirements/requirements.md` (FR-1–FR-12).
- Execution plan: `aidlc-docs/current/inception/plans/execution-plan.md` (single unit; Functional Design also covers runtime integration).
- Canonical baseline: `knowledge/opensource-lakehouse-infra-v2/application-design.md`. No Jenkins component design exists yet (CREATE `functional-design/jenkins-ci-access.md` at closure).

## Verified Findings (2026-10-31)
All checks were read-only:
- the legacy home was mounted read-only in throwaway containers
- the plugin installer ran in resolve-only mode with no download
- upstream source and docs were read at the exact release tags

| # | Topic | Finding |
|---|---|---|
| J1 | Legacy plugins | 102 plugins, all versioned, none disabled (for example `configuration-as-code 2136.veb_3a_554550b_f`, `matrix-auth 3.3`, `git 5.11.0`, `workflow-aggregator 608.v67378e9d3db_1`). |
| J2 | OIDC plugin resolution | `jenkins-plugin-cli 2.15.0 --no-download` with the 102 exact pins plus `oic-auth` resolves to **`oic-auth 4.731.v4932b_506e767`** with **zero changes** to the legacy pins. It adds only `nimbus-jose-jwt-api 10.10-12.vd4e6d651b_7f7`, and the run reported no security warnings. |
| J3 | Version status | `oic-auth 4.731.v4932b_506e767` is the latest release, requires core ≥ 2.539, and is compatible with 2.580.1. All published advisories affect older versions only. |
| J4 | Keycloak hostname | `oic-auth` manual server configuration sets `authorizationServerUrl`, `endSessionUrl`, `tokenServerUrl`, `jwksServerUrl`, `userInfoServerUrl`, and `issuer` separately. Browser endpoints use `keycloak.localhost:8080` and back-channel endpoints use `keycloak:8080`, with the canonical issuer. No network alias is needed (same approach as Airflow). |
| J5 | Configuration as code | `jenkins.securityRealm.oic` supports `clientId`, `clientSecret`, `groupsFieldName`, `userNameField`, `logoutFromOpenidProvider`, `postLogoutRedirectUrl`, `rootURLFromRequest`, and `properties` (`pkce`, `escapeHatch{username, secret, group}`). |
| J6 | Escape hatch | A plain escape-hatch secret is BCrypt-hashed by the plugin (`OicSecurityRealm.setEscapeHatchSecret`). The escape-hatch user receives the configured `group`. |
| J7 | Authorization | matrix-auth 3.3 configuration as code uses `authorizationStrategy.globalMatrix.entries` with `group:` / `user:` names and permissions (for example `Overall/Administer`, `Job/Build`). Overall/Read is required for other permissions to be usable. |
| J8 | Legacy core settings | `numExecutors=2`, `mode=NORMAL`, CSRF `DefaultCrumbIssuer`, agent port 50000, `jenkinsUrl=http://localhost:8098/`. The multibranch job holds `main` and `uat` branch histories. |
| J9 | Plugin override | The official image entrypoint copies `/usr/share/jenkins/ref/plugins` into the home only when absent, unless `PLUGINS_FORCE_UPGRADE=true`. That setting makes the image's pinned plugins authoritative over the migrated copies (C2: A). |
| J10 | Secret references | Configuration as code resolves `${readFile:/run/secrets/<file>}`, so secrets never appear in the YAML, the Compose environment, or `docker inspect`. |

## Plan Steps
- [x] Verify plugin compatibility, configuration-as-code keys, hostname handling, escape hatch, and authorization syntax (J1–J10)
- [x] Collect answers to the design questions below
- [x] Define domain entities (pinned plugin set, Jenkins home, OIDC realm, authorization matrix, escape hatch, Keycloak client, secrets)
- [x] Define business rules (authorization, migration, plugin authority, configuration as code, break-glass, legacy removal, failure behavior)
- [x] Define the business logic model (login, denial, logout, outage, start-up and migration, CI build, legacy removal)

## Design Questions

### Question 1 — Start-up when no legacy home exists
The migration copies the legacy home into `lakehouse-local_jenkins-home` once. What should core start do if that target is empty and no legacy volume exists (for example on a fresh machine, or after the legacy volume has been removed and the v2 volume is lost)?

A) Start Jenkins with an empty home: security from configuration as code, no job. Print a clear notice that the workload job is absent and must be restored from backup or recreated (Recommended)

B) Fail core start with a clear error until a home is restored

X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 2 — Legacy removal mechanism
How should the approved removal of `hive-dremio-rustfs-jenkins-1` and `iceberg-poc-jenkins-home` be performed?

A) An operator command, `scripts/lakehouse.sh remove-legacy-jenkins --confirm`. It refuses unless the v2 home carries the migration marker and v2 Jenkins is healthy, removes exactly that container and volume, and never touches `jenkins_home`. I run it only after you approve the verified Build and Test results (Recommended)

B) Documented manual `docker` commands only, with no script

X) Other (please describe after [Answer]: tag below)

[Answer]: A
