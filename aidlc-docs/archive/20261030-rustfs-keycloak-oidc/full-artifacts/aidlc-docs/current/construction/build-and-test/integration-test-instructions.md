# Integration Test Instructions — rustfs-keycloak-oidc

## Purpose
Verify RustFS ↔ Keycloak OIDC login, policy enforcement, and non-regression of Polaris STS on the local Compose stack.

## Setup
Apply the build (see `build-instructions.md`, step 4) with `keycloak`, `rustfs`, and `polaris` healthy.

## Scenarios

### Scenario 1: OIDC wiring (read-only)
```bash
python3 scripts/verify-rustfs-oidc.py
```
Expected: 7 PASS lines.
- The provider is listed.
- The authorize redirect via `localhost:9001` and via `127.0.0.1:9001` targets Keycloak with `client_id=rustfs`, the exact callback, and PKCE S256.
- Keycloak accepts both callbacks.
- The four policies match their definitions.
- The client secret is absent from `docker inspect`.

### Scenario 2: Idempotency
Rerun `infra/keycloak/bootstrap-realm.py` and `infra/rustfs/bootstrap-policies.py`. Expected (after any one-time upgrade of the exact previous definitions, reported as `updated`): success with `already-present` for all four policies and no client changes.

### Scenario 3: Polaris STS regression
```bash
python3 scripts/verify-rustfs-sts.py
```
Expected: temporary credentials limited to the dev probe path; production list/write denied; probe removed.

### Scenario 4: Headless login and authorization (temporary users)
`e2e-rustfs-oidc-login.py.txt` in this directory records the script used. Run it from a scratch location with `python3 -I <script> <repo-root>`. It creates temporary users (analyst, developer, no-group), drives the real authorize → Keycloak login → RustFS callback flow, checks S3 access with the issued session, exercises logout, and always deletes the temporary users and probe objects.

Expected:
- **Analyst**:
  - lists buckets and reads production
  - reads console metadata (`GetBucketPolicyStatus`, `GetBucketVersioning`) on production; policy status on UAT is denied
  - is denied production write, UAT read, and dev read
- **Logout**: redirects through Keycloak back to `/rustfs/console/auth/login`.
- **Developer** (logged in via `localhost`): writes dev, reads UAT, reads policy status on all three buckets, and is denied production write.
- **No-group user**: refused with "OIDC policy mapping did not resolve to current policies".

The test client clears the `Secure` flag on Keycloak cookies, which emulates how browsers treat `http://*.localhost` as a secure context.

### Scenario 5: Interactive browser login (user-confirmed, Q10: B)
Open <http://127.0.0.1:9001/rustfs/console/>, choose **Keycloak**, and sign in as a user in a product group. Confirm the bucket list and the expected access, then log out.

## Cleanup
Scenario 4 cleans up after itself. No other test data is created except the STS probe, which `verify-rustfs-sts.py` removes.
