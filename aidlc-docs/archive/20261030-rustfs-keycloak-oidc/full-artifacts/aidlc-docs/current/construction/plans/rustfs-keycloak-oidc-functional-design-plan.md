# Functional Design Plan — rustfs-keycloak-oidc

## Context
- Requirements: `aidlc-docs/current/inception/requirements/requirements.md` (FR-1–FR-11).
- Execution plan: `aidlc-docs/current/inception/plans/execution-plan.md` (single unit; Functional Design also covers runtime integration decisions).
- Canonical baselines: `knowledge/opensource-lakehouse-infra-v2/application-design.md`; `knowledge/hive-dremio-rustfs/functional-design/lakehouse-workload-and-access.md` (product access table; to be relocated per the approved inventory).

## Verified Findings (2026-10-30)

Sources: RustFS upstream source at tag `1.0.4` (read-only review of `crates/iam/src/oidc/`, `crates/iam/src/federation/mapper.rs`, `crates/utils/src/egress.rs`, `rustfs/src/admin/handlers/oidc.rs`, `rustfs/src/admin/service/federated_identity.rs`), plus a throwaway spike (temporary `rustfs/rustfs:1.0.4` container on a temporary network, tmpfs data, throwaway root keys, dummy client secret; Keycloak temporarily attached to that network with an alias, then detached). No realm, credential, or production-service change was made; the spike container and network were removed and Keycloak was confirmed back on `lakehouse-local_core` only and healthy.

| # | Question | Finding | Evidence |
|---|---|---|---|
| F1 | Does the `groups` claim map to policies? | Yes. Defaults are `claim_name=groups` and `groups_claim=groups`; each group value (plus optional `claim_prefix`) becomes a policy name. | `constants/oidc.rs`, `mapper.rs::map_policies_and_groups` |
| F2 | Unknown groups / no groups? | Group values without an existing policy are ignored. If no usable policy remains, login is rejected ("OIDC policy mapping did not resolve to current policies"). Policy lookups that fail (rather than confirm absence) also fail closed. | `federated_identity.rs::select_oidc_policies` |
| F3 | Callback URL? | `<scheme>://<request Host><`/rustfs/admin/v3/oidc/callback/default`>`, derived per request (`redirect_uri_dynamic` default on). Works on the console port; `localhost:<port>` and `127.0.0.1:<port>` each produce their own callback. | Spike: HTTP 302s from `/rustfs/admin/v3/oidc/authorize/default` |
| F4 | Static `redirect_uri` for loopback? | Not possible: config validation rejects loopback/`localhost` redirect URIs. Dynamic redirect is therefore required, and Keycloak's exact redirect list is the allowlist. | `config.rs::validate_provider_config_fields`, `egress.rs::validate_outbound_url` |
| F5 | PKCE? | RustFS always sends `code_challenge_method=S256`; confidential client + PKCE both apply. | Spike redirect |
| F6 | Reaching Keycloak from the container | Keycloak advertises `keycloak.localhost:8080` for token, JWKS, and logout endpoints even to internal callers, and RustFS has no per-endpoint override. Inside containers that name resolves (via Docker DNS forwarding) to `127.0.0.1`. A Docker network alias `keycloak.localhost` on Keycloak takes precedence and resolved to Keycloak's address in the spike. | Live discovery fetch from the `rustfs` container; spike `getent` |
| F7 | Egress policy | Private/loopback DNS results are rejected unless the exact origin is listed in `RUSTFS_OUTBOUND_ALLOW_ORIGINS`. With `http://keycloak.localhost:8080` listed, discovery and JWKS succeeded and the provider was listed. | `egress.rs`; spike `/oidc/providers` → `[{"provider_id":"default","display_name":"Keycloak"}]` |
| F8 | Client secret from file? | No `_FILE` variant exists for OIDC settings. Alternatives: an entrypoint wrapper that exports it from a mounted file, or provider config persisted through the admin API (env-managed providers cannot be edited through the API, and vice versa). | `constants/oidc.rs`, `config.rs` (`EnvironmentManaged`) |
| F9 | Session lifetime | Console OIDC sessions are issued for 3600 s (fixed in 1.0.4). Credentials reach the console in the URL fragment. | `handlers/oidc.rs` |
| F10 | Logout | RustFS supports RP-initiated logout via the discovered `end_session_endpoint`, returning to the console login page. | `handlers/oidc.rs` logout handler |

**Conclusion:** the approved mechanism (Q5: groups claim used directly as policy names) works as intended in RustFS 1.0.4. No change request is needed.

## Plan Steps
- [x] Verify RustFS 1.0.4 OIDC behavior (findings F1–F10)
- [x] Collect answers to the design questions below
- [x] Define domain entities (policy, client, provider configuration, session, secret)
- [x] Define the four policy documents and their invariants (PBT-01 property identification; PBT-02/-03 targets)
- [x] Define business rules: admission, authorization, bootstrap idempotency and conflict refusal, secret lifecycle, break-glass, failure behavior
- [x] Define the runtime integration model: name resolution, egress allowlist, secret delivery, startup ordering
- [x] Define the business logic model: login flow, denial flow, logout, Keycloak outage, operator bootstrap sequence
- [x] Record PBT framework (Hypothesis, existing `tests/requirements-pbt.txt`) per PBT-09

## Design Questions

### Question 1 — Keycloak name resolution for RustFS
How should RustFS resolve `keycloak.localhost` to the Keycloak container (F6)?

A) A dedicated internal Compose network shared only by `rustfs` and `keycloak`, where Keycloak has the alias `keycloak.localhost`; other services keep their current resolution (Recommended)

B) Add the `keycloak.localhost` alias on the existing `core` network, which also changes resolution for every other service on `core`

C) Enable Keycloak dynamic backchannel hostnames, so internal callers receive `keycloak:8080` endpoints (a Keycloak-wide behavior change)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 2 — Client secret delivery
How should the protected client secret reach RustFS (F8)?

A) A small entrypoint wrapper reads the read-only mounted secret file, exports it only into the RustFS process environment, then runs the stock image entrypoint; the secret is absent from Compose files and `docker inspect` (Recommended)

B) Configure the provider through the RustFS admin API from a bootstrap script, so the secret is stored in RustFS's own configuration on the data volume and the provider is managed by API rather than Compose

X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 3 — Owner policy breadth
What does "manage" mean for `role-default-owner` on the three buckets?

A) All S3 actions (`s3:*`) limited to the three bucket and object ARNs, including bucket configuration (Recommended)

B) Object read/write/delete plus listing and multipart only, with no bucket-configuration actions (no policy, lifecycle, versioning, or bucket deletion)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 4 — Bucket list visibility in the console
Should every OIDC user be able to list bucket names (`s3:ListAllMyBuckets`) so the console shows a bucket list?

A) Yes — all four policies include `s3:ListAllMyBuckets`; this reveals bucket names only, not contents (Recommended)

B) No — users only see buckets they reach by direct navigation

X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 5 — Logout behavior
How should console logout behave (F10)?

A) RP-initiated logout: end the Keycloak session too, with exact post-logout redirect URIs for both console hosts registered on the client (Recommended)

B) Local logout only: clear the RustFS console session and keep the Keycloak SSO session

X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 6 — When OIDC is enabled at startup
When should the RustFS OIDC provider be active?

A) Always in the core `scripts/lakehouse.sh start`; if the realm or client does not exist yet, RustFS keeps retrying discovery in the background, and root login is unaffected (Recommended)

B) Only after an explicit operator step (for example `scripts/lakehouse.sh enable-rustfs-oidc`), keeping the core start unchanged until then

X) Other (please describe after [Answer]: tag below)

[Answer]: A
