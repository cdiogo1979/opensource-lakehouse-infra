# Code Generation Plan — rustfs-keycloak-oidc

This plan is the single source of truth for Code Generation Part 2. Every step is executed in order and marked `[x]` in the same interaction it completes (DOC-02).

## Unit Context
- **Unit**: `rustfs-keycloak-oidc` (single unit; no User Stories stage — traceability is to FR-* requirements and BR-* business rules).
- **Workspace root**: `/Users/carlosdiogo/code_repo/opensource-lakehouse-infra-v2` (brownfield; modify files in place, no duplicates).
- **Design inputs**: `aidlc-docs/current/construction/rustfs-keycloak-oidc/functional-design/` (domain-entities, business-rules, business-logic-model) and findings F1–F10 in `rustfs-keycloak-oidc-functional-design-plan.md`.
- **Dependencies**: Keycloak 26.8.1 `lakehouse` realm (existing), RustFS 1.0.4 (pinned), protected runtime credentials (existing pattern). Polaris STS, bucket bootstrap, and other clients must not change behavior (FR-9, BR-19).
- **Interfaces and contracts**: Keycloak `rustfs` client and `lakehouse-rustfs-groups` mapper; RustFS `RUSTFS_IDENTITY_OPENID_*` environment; RustFS admin API `info-canned-policy` / `add-canned-policy`; the internal `lakehouse-local_rustfs-identity` network.
- **Data owned**: four RustFS IAM policies named after the product groups; the protected `rustfs-oidc-client-secret` file.
- **Not in this stage**: canonical knowledge updates (done at closure per the approved inventory); PR and deploy documents (Deploy stage); running live services (Build and Test).

## Steps

### Step 1 — Protected client secret (FR-7, BR-13)
- [x] Modify `scripts/prepare-lakehouse-runtime.py`: create `rustfs-oidc-client-secret` once with `read_or_create` (random hex), and add it to the read-only mount staging list with mode `0o644`. That matches the existing RustFS key mounts: the container user is uid 10001, and the parent `.runtime/container-mounts/` stays `0700`.

### Step 2 — RustFS entrypoint wrapper (FR-7, BR-14)
- [x] Create `infra/rustfs/rustfs-entrypoint.sh` (POSIX `sh`, run with `/bin/sh` so no host exec bit is needed). It reads `/run/secrets/rustfs_oidc_client_secret` and fails with a message that contains no secret if the file is missing, unreadable, or empty. It then exports `RUSTFS_IDENTITY_OPENID_CLIENT_SECRET` for the RustFS process only and runs `exec /entrypoint.sh "$@"`, so the stock image entrypoint and `/data` command are unchanged.

### Step 3 — Compose integration (FR-1, FR-8, BR-15, BR-16)
- [x] Modify `docker-compose.yml`:
  - **`rustfs`**: add `entrypoint: [/bin/sh, /opt/lakehouse/rustfs-entrypoint.sh]`.
  - **`rustfs` mounts**: the wrapper (`:ro`) and `.runtime/container-mounts/rustfs-oidc-client-secret:/run/secrets/rustfs_oidc_client_secret:ro`.
  - **`rustfs` environment**:
    - `RUSTFS_IDENTITY_OPENID_ENABLE=on`
    - `RUSTFS_IDENTITY_OPENID_CONFIG_URL=http://keycloak.localhost:8080/realms/lakehouse/.well-known/openid-configuration`
    - `RUSTFS_IDENTITY_OPENID_CLIENT_ID=rustfs`
    - `RUSTFS_IDENTITY_OPENID_CLAIM_NAME=groups`
    - `RUSTFS_IDENTITY_OPENID_REDIRECT_URI_DYNAMIC=on`
    - `RUSTFS_IDENTITY_OPENID_DISPLAY_NAME=Keycloak`
    - `RUSTFS_OUTBOUND_ALLOW_ORIGINS=http://keycloak.localhost:8080`
    - no client secret
  - **`rustfs` networks**: `[core, data-access, rustfs-identity]`.
  - **`keycloak` networks**: change to the map form `core: {}` plus `rustfs-identity: {aliases: [keycloak.localhost]}`.
  - **New network**: `rustfs-identity` (`name: lakehouse-local_rustfs-identity`, `internal: true`).
  - Ports, volumes, and healthchecks stay unchanged.

### Step 4 — Keycloak `rustfs` client and mapper (FR-5, BR-7, BR-8, BR-9)
- [x] Modify `infra/keycloak/bootstrap-realm.py`:
  - **Constants**: callback path, post-logout path, `RUSTFS_GROUP_MAPPER_NAME = "lakehouse-rustfs-groups"`.
  - **`rustfs_console_port()`**: reads `RUSTFS_CONSOLE_HOST_PORT` from the environment, then from `.env`, then falls back to `9001`; rejects invalid ports.
  - **`rustfs_client_configuration(secret, port)`**: confidential client, standard flow only, `webOrigins=[]`, exact `redirectUris` for `localhost` and `127.0.0.1`, attributes `pkce.code.challenge.method=S256` and `post.logout.redirect.uris` (both console hosts, `##`-separated).
  - **`ensure_rustfs_group_mapper(api, client_uuid)`**: `oidc-group-membership-mapper` with `claim.name=groups`, `full.path=false`, and `id.token.claim`, `access.token.claim`, `userinfo.token.claim` all `true`; refuses duplicate or conflicting mappers.
  - **Console-port reconciliation**: in `ensure_client`, replace the `rustfs` callback and post-logout values only when the current values exactly equal the same pattern on a different valid port. Everything else stays a conflict.
  - **`main`**: add `--rustfs-secret-file` (default `.runtime/credentials/rustfs-oidc-client-secret`); always ensure the client and mapper; report `rustfs-client=configured`.
- [x] Modify `infra/keycloak/realm-contract.json`: add the `rustfs` client entry (type, redirect URIs, post-logout URIs, PKCE, group claim, group values).

### Step 5 — RustFS policy definitions and bootstrap (FR-3, FR-4, BR-1–BR-5, BR-10–BR-12)
- [x] Modify `infra/rustfs/bootstrap-buckets.py`: generalize `S3Client.request` to accept optional `query` and `body` (canonical sorted, URI-encoded query; payload hash of the body). Existing bucket behavior stays unchanged.
- [x] Create `infra/rustfs/bootstrap-policies.py`:
  - **Pure definitions**: `BUCKETS`, `ACCESS_MATRIX`, `ACCESS_LEVEL_ACTIONS`, `policy_document(group)`, `policy_documents()`, `canonical_policy(document)`.
  - **Absent-policy detection**: `missing_canned_policy(status, body)`, ported from the legacy provisioner and kept to allowlisted error codes.
  - **`ensure_policy(client, name, document)`**: create when missing, accept when canonically equal, otherwise raise a conflict naming only the policy.
  - **`main`**: loads `S3Client` from `bootstrap-buckets.py`, signs with the protected root keys, and prints only policy names and outcomes.

### Step 6 — Operator wiring (FR-4, BR-11)
- [x] Modify `scripts/bootstrap-default-product.sh`: run `python3 infra/rustfs/bootstrap-policies.py` immediately after `bootstrap-buckets.py`.

### Step 7 — Legacy retirement (FR-10)
- [x] Delete `infra/identity-provisioner/reconcile-rustfs-roles.py`, `infra/identity-provisioner/provision-rustfs-identities.py`, and `infra/identity-provisioner/rustfs-role-policy.json`.
- [x] Modify `infra/identity-provisioner/Dockerfile`: remove the three `COPY` lines and drop `/usr/local/bin/provision-rustfs-identities` from the `chmod` line. No other change: the image was already unbuildable and is unused.

### Step 8 — Unit and property tests (BR-1–BR-19; PBT-02, -03, -07, -08, -09)
- [x] Create `tests/rustfs/test_policy_contract.py`:
  - **Example tests**: the exact four-policy matrix, `s3:ListAllMyBuckets` present, no `admin:` actions, absent-policy detection, and conflict refusal with a fake client.
  - **Hypothesis properties**: P1 round-trip, P2 order-insensitive canonicalization, P3 allow-only with resources inside the permitted ARNs, P4 union of group subsets equals the per-bucket maximum, P5 equal-iff-canonical-equal.
  - **Generators**: shared domain generators (group subsets, access levels, bucket names, shuffled documents) in `tests/rustfs/strategies.py`.
- [x] Create `tests/keycloak/test_rustfs_client_contract.py`:
  - client configuration, mapper configuration (`id.token.claim=true`), and port resolution order;
  - port-change reconciliation, with any other URI change refused;
  - secret mismatch refusal and a contract JSON entry that matches the code.
- [x] Create `tests/rustfs/test_compose_oidc_contract.py`:
  - **RustFS environment**: the exact OIDC keys and values, no `CLIENT_SECRET` anywhere in Compose, and the exact allowlist.
  - **Network**: the identity network is `internal`, the `keycloak.localhost` alias exists only there, and RustFS and Keycloak are its only members.
  - **Wrapper**: the wrapper script contract.
  - **Credentials**: `prepare-lakehouse-runtime.py` stages the new secret.
- [x] Create `tests/rustfs/test_legacy_retirement.py`: the retired files are absent and no repository file outside `aidlc-docs/` references them.

### Step 9 — Live verification helper (Build and Test hooks)
- [x] Create `scripts/verify-rustfs-oidc.py`: read-only checks against the running stack.
  - The provider `default` is listed.
  - The authorize redirect from both `localhost` and `127.0.0.1` console hosts targets the Keycloak authorize endpoint with `client_id=rustfs` and the exact registered callback.
  - The four policies are present and canonically equal to their definitions (signed admin GET).
  - The `rustfs` container's inspected environment contains no client secret.
  - Prints pass/fail per check and no secrets.

### Step 10 — Documentation (FR-6, FR-11)
- [x] Modify `README.md`: add a "RustFS console OIDC login" section.
  - sign-in, the group-to-policy table, and root break-glass;
  - bootstrap order and `scripts/verify-rustfs-oidc.py`;
  - secret rotation, logout, and outage behavior;
  - the console-port note (logins must start on the console port).
  - Also remove any reference to the retired provisioner files.
- [x] Create `aidlc-docs/current/construction/rustfs-keycloak-oidc/code/code-summary.md`: modified/created/deleted files, with requirement and rule traceability.

### Step 11 — Change request from Build and Test: console metadata access (FR-3, BR-5, BR-10a)
- [x] Modify `infra/rustfs/bootstrap-policies.py`: add read-only console metadata actions to the `read` level (so also `read_write`), keep the previous definitions, and upgrade an existing policy only when it exactly equals its previous definition, re-reading to verify.
- [x] Modify `tests/rustfs/test_policy_contract.py`: updated read set, console-metadata, upgrade, and previous-vs-current tests; P5 now covers accept / upgrade / refuse.
- [x] Apply and re-verify live: three policies `updated`, owner `already-present`, rerun idempotent, `verify-rustfs-oidc.py` passes, headless E2E 19/19.

### Step 12 — Change request from Build and Test: upstream console limitation (clarification Q3: A)
- [x] Modify `README.md`: document the non-admin bucket-list loop (rustfs/console#271), the bucket deep-link workaround, and the upgrade follow-up.

## Traceability
| Requirement | Steps |
|---|---|
| FR-1 Console OIDC login | 3, 4 |
| FR-2 Admission | 5 (native refusal via policies), 8, 9 |
| FR-3 Authorization by group | 5, 8 |
| FR-4 Policy provisioning | 5, 6, 8 |
| FR-5 Keycloak client bootstrap | 4, 8 |
| FR-6 Root break-glass | 3 (unchanged root config), 10 |
| FR-7 Secret handling | 1, 2, 3, 8, 9 |
| FR-8 Container-reachable IdP | 3, 8, 9 |
| FR-9 No regression | 3, 5 (bucket client unchanged), Build and Test |
| FR-10 Legacy retirement | 7, 8 |
| FR-11 Documentation and knowledge | 10 (knowledge at closure) |

## Scope
10 steps, 16 file operations: 8 modified, 7 created plus a code summary, 3 deleted.
