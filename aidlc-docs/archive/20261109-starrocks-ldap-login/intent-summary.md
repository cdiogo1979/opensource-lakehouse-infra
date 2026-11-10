# Intent Summary: StarRocks LDAP Login

## Intent
StarRocks LDAP Login (`20261109-starrocks-ldap-login`)

## Objective
Let users, including service users, log in to StarRocks with their own username and password: a lightweight LDAP directory as the shared password store, Keycloak federating its users, StarRocks checking passwords against LDAP over TLS.

## Date
2026-11-09

## Scope
Included: OpenLDAP service (own image), LDAP TLS material and secrets, Keycloak writable federation, StarRocks forced TLS and LDAP password login, user-sync switch from JWT, password login client, retirement of the starrocks token client and starrocks-token.sh, one-time resumable user migration incl. Jupyter homes, Hub maintenance service, README, tests (PBT partial). Excluded: groups in LDAP, long-lived BI tokens, FreeIPA and Kerberos, LDAP HA.

## Units / workstreams
ldap-password-login

## Major requirements
- FR-1 OpenLDAP directory (own Alpine image, LDAPS only, Argon2, no host port, least-privilege ACLs)
- FR-2 Keycloak writable LDAP federation; groups stay in Keycloak; user scripts unchanged
- FR-3 StarRocks LDAP password login with forced TLS; user sync switches JWT users in place
- FR-4 password login client; token client and starrocks-token.sh retired
- FR-5 one-time resumable migration with known passwords, verification before deletion, and Jupyter home copy
- FR-6 fresh installs create users in LDAP; FR-7 tests incl. Hypothesis properties (partial)

## Architecture and design decisions
- Lightweight OpenLDAP instead of FreeIPA (evaluation before the intent)
- Password-only StarRocks login: one login method per StarRocks user (probed)
- Writable federation with Keycloak's default mappers; groups kept in Keycloak
- ssl_force_secure_transport for every StarRocks connection; the scheduled sync verifies the StarRocks CA
- StarRocks binds as the user (direct bind pattern), holding no LDAP secret
- Migration writes and verifies the LDAP entry before deleting the local Keycloak copy (Keycloak refuses duplicates and deleting a federated user deletes its entry)
- Old Jupyter home volumes and Hub users are deleted after a verified copy, through a Hub maintenance service limited to admin:users

## Implementation decisions
- infra/ldap entrypoint renders slapd.conf with hashed secrets, seeds only an empty volume, and refreshes the Keycloak bind hash with slapmodify at every start
- infra/keycloak/ldap_federation.py ensures the provider and runs Keycloak's bind test, resending the credential once if the bind fails
- infra/keycloak/ldap_people.py is the pure model for entries, password sources, and the migration plan
- The LDAP bind pattern is a runtime setting (starrocks_common.ensure_ldap_login), set by the runtime bootstrap and re-applied by every user sync
- Migration state in .runtime/state/ldap-migration.json lets a rerun finish users interrupted after deletion

## Deviations
- fe.conf could not hold the bind pattern (it expands ${USER} as an environment variable); moved to runtime with self-heal (Build and Test finding)
- The ldapi socket directory was missing in the image (found in the standalone test, fixed)

## Verification
See construction/build-and-test/build-and-test-summary.md. Live: start with federation; migration of 5 users (backup, verified binds, import, restore, Jupyter home copy, token client removed, JWT users switched); Keycloak sign-ins; StarRocks password logins for people and a service user with exact roles; wrong-password and plain-text refusals; password-change propagation; new user and product writer in LDAP; Connector/J REQUIRED and VERIFY_IDENTITY; writer token, role matrix, RustFS OIDC, scheduled sync over TLS, bind-pattern self-heal. Suite 354 passed, 1 skipped, 1 known Airflow drift failure. Not run: interactive JupyterHub/Airflow/DBeaver sign-ins of migrated users, destructive reset and fresh install, Airflow DAG run.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/starrocks-sql-access.md

## Superseded decisions
- StarRocks token login (authentication_jwt, the starrocks Keycloak client, starrocks-token.sh, DBeaver idTokenFile) replaced by LDAP password login over forced TLS
- Users stored in Keycloak's own database replaced by users in the LDAP directory (Keycloak writable federation)
- The scheduled sync's --skip-ssl replaced by verified TLS
- The BI follow-up premise (long-lived tokens required) is relaxed: BI tools can use username and password

## Archived artifacts
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/aidlc-docs/current/compaction/20261109-starrocks-ldap-login/manifest.json
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/starrocks-sql-access.md
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/infra/ldap/Dockerfile
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/infra/ldap/ldap-entrypoint.sh
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/infra/ldap/slapd.conf.template
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/scripts/setup/prepare-ldap-certificates.py
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/scripts/setup/prepare-runtime.py
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/scripts/lakehouse.sh
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/scripts/operations/reset-lakehouse.py
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/scripts/operations/migrate-users-to-ldap.py
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/infra/keycloak/ldap_federation.py
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/infra/keycloak/ldap_people.py
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/infra/keycloak/bootstrap-realm.py
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/infra/keycloak/realm-contract.json
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/infra/starrocks/conf/fe.conf
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/infra/starrocks/starrocks_common.py
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/infra/starrocks/bootstrap-starrocks.py
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/infra/starrocks/reconcile-starrocks-users.py
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/scripts/clients/starrocks-login.sh
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/infra/jupyter/hub/jupyterhub_config.py
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/compose.core.yml
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/compose.starrocks.yml
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/compose.jupyter.yml
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/README.md
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/tests/ldap
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/tests/starrocks/test_starrocks_properties.py
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/tests/starrocks/test_starrocks_bootstrap_contract.py
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/tests/starrocks/test_starrocks_compose_contract.py
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/tests/starrocks/starrocks_strategies.py
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/tests/jupyterhub/test_config_contract.py
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/tests/operations/test_compose_modules_contract.py
- aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/tests/operations/test_reset_lakehouse.py

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261109-starrocks-ldap-login/full-artifacts/`
