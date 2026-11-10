# Deployment Instructions: RustFS Keycloak OIDC login

> These instructions document the steps. They do not authorize or perform a deployment. Run every command from the repository root. All steps are manual operator actions unless marked automated.

**Target**: the local Docker Compose lakehouse stack (Compose project `lakehouse-local`), loopback only.
**Path A**: an existing running stack. This is the change applied during Build and Test on 2026-10-30.
**Path B**: a fresh install.

## Path A — existing stack

### Step 1 — Back up state
- **Action and target**: back up `.runtime/credentials/` and the volumes `lakehouse-local_keycloak-db-data` and `lakehouse-local_rustfs-data`.
- **Prerequisites**: encrypted backup storage. Stop the owning services if you take volume-level backups (README, "State and backup").
- **Execution**: follow the README backup guidance. Never use `docker compose down -v`.
- **Validation**: the backup exists and is readable.
- **Failure handling**: do not continue without a backup.

### Step 2 — Create the protected client secret (automated script)
- **Action and target**: create `.runtime/credentials/rustfs-oidc-client-secret` once, plus its read-only container mount copy.
- **Execution**: `python3 scripts/prepare-lakehouse-runtime.py`
- **Validation**: both files exist. The credentials copy has mode `0600`. No value is printed.
- **Failure handling**: the script never replaces existing credentials. Resolve any reported unreadable or empty file before continuing.

### Step 3 — Recreate Keycloak and RustFS with the new configuration
- **Action and target**: Compose services `keycloak` and `rustfs`. This creates the internal network `lakehouse-local_rustfs-identity`.
- **Prerequisites**: Steps 1–2 done. Expect a brief Keycloak interruption for Airflow, JupyterHub, and Polaris token validation.
- **Execution**: `docker compose -f docker-compose.yml up -d keycloak rustfs`
- **Validation**:
  - both services report `healthy`
  - `docker exec lakehouse-local-rustfs-1 getent hosts keycloak.localhost` returns a private address, not `127.0.0.1`
- **Failure handling**: if RustFS exits with "client secret file is unavailable/empty", repeat Step 2 and then this step. Root-key access is unaffected throughout.

### Step 4 — Configure the Keycloak `rustfs` client and mapper (automated script)
- **Action and target**: the Keycloak `lakehouse` realm. It adds the `rustfs` client, its exact callback and post-logout URIs for the console port (`RUSTFS_CONSOLE_HOST_PORT`, default 9001), and the `lakehouse-rustfs-groups` mapper.
- **Prerequisites**: Keycloak is healthy.
- **Execution**: `python3 infra/keycloak/bootstrap-realm.py`. If the Airflow client is managed in this environment, use `scripts/lakehouse.sh start-airflow` or pass `--airflow-secret-file .runtime/credentials/keycloak-airflow-client-secret` as usual. Without that flag the Airflow client is left untouched.
- **Validation**: the output ends with `rustfs-client=configured`. A rerun gives the same result and makes no changes.
- **Failure handling**: the script refuses conflicting client, secret, URI, or mapper settings and changes nothing. Review the named conflict manually; do not delete the client to force it.

### Step 5 — Create the product-group RustFS policies (automated script)
- **Action and target**: RustFS IAM policies `role-default-owner`, `role-default-developer`, `role-default-analyst`, `role-default-writer`.
- **Prerequisites**: RustFS is healthy. The environment buckets exist (`python3 infra/rustfs/bootstrap-buckets.py`).
- **Execution**: `python3 infra/rustfs/bootstrap-policies.py`
- **Validation**: each policy reports `created`, `updated` (only for the exact previous definition), or `already-present`. A rerun reports `already-present` for all four.
- **Failure handling**: a conflicting existing policy is refused and left unchanged. Reconcile it manually with the root identity after review.

### Step 6 — Verify (read-only, automated)
- **Execution**:
  ```bash
  python3 scripts/verify-rustfs-oidc.py      # expect 7 PASS lines
  python3 scripts/verify-rustfs-sts.py       # Polaris STS regression; uses and removes a dev probe object
  PYTHONPATH=infra/jupyter/hub python3 -m pytest -q tests --hypothesis-seed=<seed>
  ```
- **Validation**:
  - both scripts pass
  - the RustFS, Keycloak, and Polaris suites pass
  - the two pre-existing Airflow role-mapping test failures are unrelated
- **Failure handling**: stop and investigate before announcing availability.

### Step 7 — Interactive check (manual)
- **Execution**:
  1. Open <http://127.0.0.1:9001/rustfs/console/>, choose **Keycloak**, and sign in as a product-group user.
  2. Open a bucket directly, for example `/rustfs/console/browser?bucket=bucket-default-dev`.
  3. Log out.
- **Validation**: bucket access matches the user's group, and logout returns to the console login page.
- **Known limitation**: the bucket-list page (`/rustfs/console/browser/`) loops for OIDC users because of upstream console bug rustfs/console#271. Use bucket links until RustFS bundles console v0.1.38 or later.

## Path B — fresh install
1. `cp .env.example .env` and `./scripts/lakehouse.sh start`. This prepares credentials (including the RustFS OIDC secret), starts the stack with the new network and OIDC configuration, and runs the realm bootstrap (including the `rustfs` client).
2. `scripts/bootstrap-default-product.sh`. This provisions buckets and then the four RustFS policies, along with the rest of the product bootstrap.
3. Steps 6–7 above.

RustFS starts before the Keycloak realm exists and retries provider discovery in the background. Login becomes available after step 1 completes.

## Rollback
No automated rollback is designed.
- **Disable OIDC login**: revert `docker-compose.yml` (RustFS OIDC environment, entrypoint, mounts, network; Keycloak network alias) and the bootstrap scripts, then run `docker compose -f docker-compose.yml up -d keycloak rustfs`. Root-key access and Polaris STS are unaffected.
- **Leftovers**: the Keycloak `rustfs` client and mapper, the four RustFS policies, and the secret file stay in place but do nothing without the RustFS provider. There is no removal script. Remove them manually (Keycloak admin console, RustFS root identity) only if required. Treat removal as its own reviewed change.
- **If storage access regresses**: if any step breaks Polaris STS or bucket access, restore from the Step 1 backup.

## Inputs and blockers
- No blockers for the local stack.
- **Before any shared or production use**: decide on TLS, non-loopback hostnames, the Keycloak administration identity used by bootstraps (currently the local bootstrap admin), and the RustFS release that bundles console v0.1.38 or later.
