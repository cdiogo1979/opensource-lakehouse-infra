# Intent Summary: Jenkins Onboarding and Keycloak SSO

## Intent
Jenkins Onboarding and Keycloak SSO (`20261031-jenkins-keycloak-sso`)

## Objective
Bring the pre-v2 Jenkins CI for the opensource-lakehouse workload repository into the v2 Compose stack and replace its shared local admin with Keycloak SSO and group-based permissions.

## Date
2026-10-31

## Scope
Migrated (copied) legacy Jenkins home, pinned 2.580.1 image with exact plugins plus oic-auth, security configuration as code, Keycloak jenkins client and groups mapper, protected secrets and escape hatch, loopback Compose service in core start, guarded legacy removal (executed after approval), tests, README, and Deploy handoff. Excluded: a job for the infrastructure repository, Docker or remote agents, webhooks and GitHub tokens, edits to opensource-lakehouse, Jenkins upgrades, and non-loopback exposure.

## Units / workstreams
Pinned image and plugins, Security configuration as code and Keycloak jenkins client, Home migration, Compose service, and core-start wiring, Legacy removal, tests, Build and Test, and Deploy handoff

## Major requirements
- Jenkins runs in the v2 core stack on 127.0.0.1:8090 from a copy of the legacy home that preserves the opensource-lakehouse multibranch job and history.
- Keycloak SSO with tiered group permissions (owner Administer; developer read and build; analyst read-only; writer and no-group denied) and an escape-hatch break-glass admin.
- Exact plugin pinning (legacy versions plus oic-auth), with the image authoritative over the home; security configuration as code reapplied at every start.
- Built-in-node executors without the Docker socket; anonymous GitHub polling; guarded removal of the legacy container and volume after verification.

## Architecture and design decisions
- Copy, not adopt, the legacy volume; never overwrite a non-empty home; write the origin marker only after verification; start empty with a notice when no legacy home exists.
- oic-auth 4.731.v4932b_506e767 resolves with all 102 legacy pins unchanged (adds nimbus-jose-jwt-api); PLUGINS_FORCE_UPGRADE makes the image authoritative.
- Manual OIDC endpoints: browser on keycloak.localhost, back-channel on keycloak:8080, canonical issuer; no network alias needed.
- Secrets via ${trim:${readFile:...}}; escape-hatch user in its own Administer group; global matrix with no anonymous, authenticated, or writer entries.

## Implementation decisions
- bootstrap-realm.py gained the jenkins client and mapper; port lookup, loopback URI, port-move reconciliation, and ID-token group mapper helpers are now shared with RustFS.
- scripts/migrate-jenkins-home.py has a pure decision table (skip, refuse-unmarked, refuse-legacy-running, copy, fresh) and copies in throwaway containers with a read-only source.
- scripts/lakehouse.sh builds, migrates, starts, and waits for Jenkins in core start and adds remove-legacy-jenkins --confirm; verify-jenkins-oidc.py provides read-only live checks.

## Deviations
- The workload CI build criterion was waived: the pipeline ran correctly but opensource-lakehouse commit 00b6623 broke one unit test.
- The first headless test run had test-script defects (a tuple comparison and the escape-hatch form/crumb); they were fixed and the run repeated.
- Legacy removal was executed only after the user approved Build and Test and confirmed the interactive login.

## Verification
Passed: verify-jenkins-oidc 9/9 (also after restart); idempotent reruns; plugin parity with plugins.txt; verified home copy; headless SSO and permission matrix with temporary users (owner, developer, analyst, writer, no-group; escape hatch; logout); RustFS, Airflow, and JupyterHub unaffected; interactive login confirmed by the user. Full suite 174 passed, 1 skipped, 2 pre-existing Airflow failures. WAIVED (user-accepted, not a pass): a successful workload CI build. main #11 and uat #4 ran the full pipeline on v2 and failed on one opensource-lakehouse unit test after commit 00b6623 ('rename dag'), a workload regression outside scope.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/jenkins-ci-access.md

## Superseded decisions
- Jenkins moved from deferred (docker-compose.deferred.yml: unsupported-pending-migration) to implemented in the main Compose stack.
- The legacy instance's local-user security realm and 'logged-in users can do anything' authorization were replaced by OIDC and the global matrix; the legacy port 8098 on all interfaces was replaced by 127.0.0.1:8090.

## Archived artifacts
- aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/aidlc-docs/current/compaction/20261031-jenkins-keycloak-sso/manifest.json
- aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/infra/jenkins/Dockerfile
- aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/infra/jenkins/plugins.txt
- aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/infra/jenkins/casc/jenkins.yaml
- aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/infra/keycloak/bootstrap-realm.py
- aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/infra/keycloak/realm-contract.json
- aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/scripts/prepare-lakehouse-runtime.py
- aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/scripts/migrate-jenkins-home.py
- aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/scripts/verify-jenkins-oidc.py
- aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/scripts/lakehouse.sh
- aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/docker-compose.yml
- aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/docker-compose.deferred.yml
- aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/.env.example
- aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/README.md
- aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/tests/jenkins
- aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/tests/keycloak/test_jenkins_client_contract.py

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261031-jenkins-keycloak-sso/full-artifacts/`
