# Intent Summary: RustFS Keycloak OIDC Login

## Intent
RustFS Keycloak OIDC Login (`20261030-rustfs-keycloak-oidc`)

## Objective
Enable RustFS console sign-in through the existing Keycloak lakehouse realm, authorizing users by product group while keeping root static keys as break-glass.

## Date
2026-10-30

## Scope
Local Compose RustFS 1.0.4 console OIDC login: Keycloak rustfs client and groups mapper, four group-named RustFS policies, protected client-secret delivery, scoped Keycloak name resolution and egress allowlist, retirement of FreeIPA-era RustFS identity scripts, tests, README, and Deploy handoff. Excluded: programmatic AssumeRoleWithWebIdentity, RustFS server administration via OIDC, MFA, non-loopback exposure, and changes to JupyterHub, Airflow, or Polaris authentication. No production deployment or PR creation.

## Units / workstreams
Keycloak rustfs client, exact callbacks, and ID-token groups mapper, RustFS product-group policies and policy bootstrap, RustFS OIDC Compose wiring, identity network, and secret wrapper, Legacy retirement, tests, Build and Test, and Deploy handoff

## Major requirements
- RustFS console Authorization Code login through a dedicated confidential Keycloak client; all four product groups admitted; users without a product group refused.
- Group-named RustFS policies mirror the data-role model on the three environment buckets; no RustFS server administration via OIDC.
- Root static-key console login retained as documented break-glass; Polaris STS and bucket bootstrap unchanged.
- Client secret kept in a protected file and out of Compose configuration; FreeIPA-era RustFS identity scripts retired; hive-dremio-rustfs knowledge retired.

## Architecture and design decisions
- Use the ID-token groups claim directly as RustFS policy names (RustFS default claim_name=groups); unknown group values are ignored and an empty resolution refuses the session.
- Dynamic redirect URIs with exact Keycloak callbacks for localhost and 127.0.0.1 on the console port (static loopback redirect URIs are rejected by RustFS).
- Internal rustfs-identity network with Keycloak alias keycloak.localhost and exact RUSTFS_OUTBOUND_ALLOW_ORIGINS, so the advertised issuer endpoints are reachable from RustFS only.
- Entrypoint wrapper exports the client secret from a mounted file because RustFS 1.0.4 has no file-based OIDC secret setting.
- Owner gets s3:* on the three buckets; read levels include read-only console metadata actions; all policies list bucket names; RP-initiated logout with exact post-logout URIs; OIDC always enabled in core start.

## Implementation decisions
- bootstrap-realm.py always ensures the rustfs client and lakehouse-rustfs-groups mapper (id.token.claim=true), resolves the console port from env, .env, then 9001, and reconciles only an exact console-port change.
- bootstrap-policies.py defines the policies, compares canonical forms, refuses conflicts, and upgrades only the exact previous definition; it reuses the generalized SigV4 client in bootstrap-buckets.py.
- verify-rustfs-oidc.py provides read-only live verification; Hypothesis properties P1-P5 cover policy round-trip, ordering, scope, group union, and acceptance.

## Deviations
- Change Request 1: the console bucket list looped on denied GetBucketPolicyStatus; read levels gained read-only console metadata actions and the bootstrap gained an exact-previous-definition upgrade (BR-10a).
- Change Request 2: the console still looped for every OIDC session due to upstream rustfs/console#271 (fixed in console v0.1.38; RustFS 1.0.4 embeds v0.1.37). Accepted as a documented limitation with a bucket deep-link workaround and an upgrade follow-up.
- The knowledge application design records the pre-existing Airflow role-mapping drift (code maps role-default-developer to User; tests and the approved table expect Admin) for a dedicated change.

## Verification
Unit/contract/property suites for this intent passed (84; full suite 137 passed, 1 skipped, 2 pre-existing Airflow role-mapping failures outside scope). Live: verify-rustfs-oidc 7/7, bootstrap idempotency, Polaris STS regression, headless login and authorization with temporary users 19/19, and an interactive developer console login confirmed by the user through a bucket view. Known upstream limitation: the RustFS 1.0.4 console bucket-list page loops for OIDC non-admin users (rustfs/console#271); bucket deep-link workaround documented. Performance and vulnerability scanning were not run.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md

## Superseded decisions
- The first approved read access level (GetBucketLocation, ListBucket, GetObject) was replaced by the level including console metadata reads; the original definitions remain in the archived functional design and plans.

## Archived artifacts
- aidlc-docs/archive/20261030-rustfs-keycloak-oidc/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261030-rustfs-keycloak-oidc/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261030-rustfs-keycloak-oidc/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261030-rustfs-keycloak-oidc/full-artifacts/aidlc-docs/current/compaction/20261030-rustfs-keycloak-oidc/manifest.json
- aidlc-docs/archive/20261030-rustfs-keycloak-oidc/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/archive/20261030-rustfs-keycloak-oidc/full-artifacts/aidlc-docs/knowledge/hive-dremio-rustfs
- aidlc-docs/archive/20261030-rustfs-keycloak-oidc/full-artifacts/docker-compose.yml
- aidlc-docs/archive/20261030-rustfs-keycloak-oidc/full-artifacts/infra/rustfs/rustfs-entrypoint.sh
- aidlc-docs/archive/20261030-rustfs-keycloak-oidc/full-artifacts/infra/rustfs/bootstrap-policies.py
- aidlc-docs/archive/20261030-rustfs-keycloak-oidc/full-artifacts/infra/rustfs/bootstrap-buckets.py
- aidlc-docs/archive/20261030-rustfs-keycloak-oidc/full-artifacts/infra/keycloak/bootstrap-realm.py
- aidlc-docs/archive/20261030-rustfs-keycloak-oidc/full-artifacts/infra/keycloak/realm-contract.json
- aidlc-docs/archive/20261030-rustfs-keycloak-oidc/full-artifacts/infra/identity-provisioner/Dockerfile
- aidlc-docs/archive/20261030-rustfs-keycloak-oidc/full-artifacts/scripts/prepare-lakehouse-runtime.py
- aidlc-docs/archive/20261030-rustfs-keycloak-oidc/full-artifacts/scripts/bootstrap-default-product.sh
- aidlc-docs/archive/20261030-rustfs-keycloak-oidc/full-artifacts/scripts/verify-rustfs-oidc.py
- aidlc-docs/archive/20261030-rustfs-keycloak-oidc/full-artifacts/README.md
- aidlc-docs/archive/20261030-rustfs-keycloak-oidc/full-artifacts/tests/rustfs
- aidlc-docs/archive/20261030-rustfs-keycloak-oidc/full-artifacts/tests/keycloak/test_rustfs_client_contract.py

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261030-rustfs-keycloak-oidc/full-artifacts/`
