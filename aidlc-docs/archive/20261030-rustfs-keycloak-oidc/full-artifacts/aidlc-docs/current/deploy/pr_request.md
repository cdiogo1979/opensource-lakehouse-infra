# Proposed PR: RustFS console login through Keycloak OIDC

> Proposed PR description only. No pull request has been created. This workspace has no Git metadata.

## Problem
The RustFS console accepted only the root access key and secret key. Every human who needed the console shared root, which gave them unrestricted access to all buckets and server administration. That did not match the platform's Keycloak-based product roles.

## Solution
Enable RustFS 1.0.4's native OpenID Connect login against the existing Keycloak `lakehouse` realm, and authorize users by their product group.

- **Dedicated client**: a confidential `rustfs` Keycloak client (Authorization Code with PKCE S256). It has exact callback and post-logout URIs for `localhost` and `127.0.0.1` on the console port, and a `groups` claim in the ID token.
- **Group-named policies**: RustFS reads each `groups` value as a policy name. Four RustFS policies named after the product groups mirror the data-role model on the three environment buckets:
  - owner: all S3 actions
  - developer: read everywhere, write dev
  - analyst: read production
  - writer: read/write everywhere

  Read levels also include the read-only metadata the console needs. Users without a product group are refused a session. No policy grants RustFS administration.
- **Reaching Keycloak from RustFS**: Keycloak advertises `keycloak.localhost`, which resolves to loopback inside containers. An internal `rustfs-identity` network, where Keycloak carries that alias, plus an exact RustFS egress allowlist, keep the canonical issuer working without affecting other services.
- **Client secret**: a protected file is exported into the RustFS process by a small entrypoint wrapper. It never appears in Compose files or `docker inspect`.
- **Bootstrap safety**: realm and policy bootstraps only add what is missing and refuse conflicts. The one exception is that a policy exactly matching its previous approved definition is upgraded in place.
- **Break-glass**: root login stays available and documented.

## Main changes
- `docker-compose.yml`:
  - RustFS: OIDC settings, egress allowlist, secret and wrapper mounts, `rustfs-identity` network.
  - Keycloak: alias on that network only.
  - New internal network.
- `infra/rustfs/rustfs-entrypoint.sh` (new): exports the client secret, then runs the stock entrypoint.
- `infra/rustfs/bootstrap-policies.py` (new): the four group-named policies, with verification and exact-previous upgrade.
- `infra/rustfs/bootstrap-buckets.py`: the signer gained query and body support; bucket behavior is unchanged.
- `infra/keycloak/bootstrap-realm.py`, `infra/keycloak/realm-contract.json`:
  - the `rustfs` client and `lakehouse-rustfs-groups` mapper
  - console-port resolution
  - exact-pair port-change reconciliation
- `scripts/prepare-lakehouse-runtime.py`: creates and stages `rustfs-oidc-client-secret`.
- `scripts/bootstrap-default-product.sh`: runs the policy bootstrap after the bucket bootstrap.
- `scripts/verify-rustfs-oidc.py` (new): read-only live verification.
- Retired the FreeIPA-era `infra/identity-provisioner/{reconcile-rustfs-roles.py, provision-rustfs-identities.py, rustfs-role-policy.json}` and their Dockerfile references.
- Tests (new):
  - `tests/rustfs/` — policy matrix, Hypothesis properties, Compose/wrapper contracts, legacy retirement
  - `tests/keycloak/test_rustfs_client_contract.py`
- `README.md`: RustFS console OIDC section, covering sign-in, groups, break-glass, rotation, logout, outage behavior, and the known limitation.

## Verification
Build and test ran on the local Compose stack on 2026-10-30.

**Automated tests**
| Suite | Result |
|---|---|
| Suites for this change (`tests/rustfs`, `tests/keycloak`, `tests/polaris`) | 84 passed |
| Full suite | 137 passed, 1 skipped, 2 failed |

The 2 failures are pre-existing and unrelated (see Risks).

**Live checks**
| Check | Result |
|---|---|
| `scripts/verify-rustfs-oidc.py` | 7/7 |
| Bootstrap reruns | Idempotent |
| Polaris STS regression (`scripts/verify-rustfs-sts.py`) | Pass |
| Headless login and authorization with temporary users (deleted afterwards) | 19/19 |

The headless test confirmed:
- Each role gets exactly its access.
- Users without a group are refused.
- Logout goes through Keycloak back to the console login page.

**Interactive check**: console login was confirmed in a browser as a developer user, through a bucket view.

**Not run**: performance tests (no requirements) and vulnerability scanning (Security Baseline extension not enabled). No formatter or linter is configured in this repository.

## Deployment
Ordered steps are required. See [`deploy_instructions.md`](deploy_instructions.md):
1. Back up.
2. Create the client secret.
3. Recreate `keycloak` and `rustfs`.
4. Run the realm bootstrap.
5. Run the policy bootstrap.
6. Verify.

Recreating Keycloak briefly interrupts Keycloak logins for Airflow, JupyterHub, and Polaris token validation.

## Risks and limitations
- **Known upstream console bug.** RustFS 1.0.4 embeds console v0.1.37. Its bucket-list page loops for non-admin users, which includes every OIDC user ([rustfs/console#271](https://github.com/rustfs/console/issues/271)). The fix is in console v0.1.38, which no RustFS release bundles yet. Workaround: open a bucket directly, at `/rustfs/console/browser?bucket=<name>`. Follow-up: adopt the first RustFS release that bundles console v0.1.38 or later, and re-check the console's metadata needs then.
- **Sessions.** Console sessions last one hour. Existing sessions keep working until expiry if Keycloak becomes unavailable. RustFS 1.0.4 accepts the OIDC client secret only as an environment variable; the wrapper limits it to the RustFS process environment.
- **Callbacks.** Only console-port callbacks are registered, so logins started on the S3 port are refused by Keycloak.
- **Writer group.** Interactive use of the `role-default-writer` group needs a human user in that service group. None was created.
- **Unrelated pre-existing issues, not changed here:**
  - `tests/airflow/test_keycloak_sso_contract.py` (2 tests) still expects `role-default-developer → Admin`; the Airflow mapping was changed to `User` before this work started.
  - CI cannot collect `tests/jupyterhub/test_unit2_token_broker.py`, which needs `jupyterhub` and `PYTHONPATH=infra/jupyter/hub`.
  - The remaining `infra/identity-provisioner` image was already unbuildable and is unused.
- **Not production-ready.** This is a local, single-node, loopback-only setup, not a production or high-availability certification.
