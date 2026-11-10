# Unit 2 Code Generation Plan — Hub Token Broker and Spark Session Identity

## Purpose

Implement the approved Unit 2 outcome: each Jupyter user's Spark session obtains that user's current Keycloak access JWT through an authenticated, hostname-verified internal HTTPS broker; the Hub retains refresh tokens and OAuth client secrets; Spark uses the exact user JWT for Polaris REST requests. This is the single source of truth for Unit 2 Code Generation. Test sources may be added as planned; their execution belongs to Build and Test.

## Unit context and contracts

- **Stories:** US-03 (Start Spark with my current identity) and Unit 2 responsibilities of US-06 (safe identity binding, errors, and token-free diagnostics).
- **Requirements:** FR-3, FR-4 client handoff, FR-7 token isolation; approved token lifecycle, performance, refresh, TLS, and observability NFRs.
- **Dependencies:** Approved Unit 1 OIDC Hub and per-user Spark container; Unit 2 Functional, NFR, and Infrastructure Design; existing Keycloak `lakehouse` realm; Polaris Iceberg REST endpoint.
- **Hub contract:** Validate the caller's own JupyterHub server API token, derive the user/server binding from Hub-owned state, read/update only that user's encrypted auth state, and return access token plus expiry only.
- **Spark contract:** Before each Spark session, call the Hub broker over verified HTTPS; configure the exact returned JWT in memory as the Polaris Bearer token; do not persist or log it.
- **Refresh contract:** Reuse only when more than 60 seconds remain; otherwise acquire a per-user async lock, reread state, refresh with a hard five-second Keycloak timeout, do not replay, reread state once after ambiguous timeout, and fail closed if no valid rotated token exists.
- **Infrastructure contract:** Keep the broker inside the Hub process on `jupyter-user` stable address port 8443; no host-published broker port. Use host-prepared CA/server files, Hub-only server key mount, and read-only user CA certificate mount. Preserve the `core`, `jupyter-user`, and `data-access` boundaries.
- **Exclusions:** No new service, database, queue, distributed lock, Prometheus endpoint, identity/role changes, Polaris grants, RustFS root credential, public ingress, or automatic group-revocation watcher.

## Code targets

Modify existing files in place and add only these implementation/test/documentation targets:

- `infra/jupyter/hub/jupyterhub_config.py`
- New `infra/jupyter/hub/lakehouse_token_broker.py`
- `infra/jupyter/hub/requirements.txt` and `infra/jupyter/hub/requirements-lock.txt` only if a required compatible dependency is missing; retain exact pins.
- New `infra/jupyter/singleuser/lakehouse_broker_client.py`
- New `infra/jupyter/singleuser/lakehouse_spark.py` as the supported Spark-session factory that obtains a token and applies it to the Iceberg REST catalog in memory.
- `infra/jupyter/singleuser/start-session.sh` only if needed to preserve safe process startup; do not put bearer values in shell arguments or exports.
- `infra/jupyter/singleuser/spark-defaults.conf` only for non-secret defaults (never a token).
- `infra/jupyter/hub/Dockerfile` and `infra/jupyter/singleuser/Dockerfile` only for the minimal pinned runtime dependencies or copied modules required by the broker/client.
- `docker-compose.yml` for the `jupyter-user` IPAM/stable Hub address, internal port configuration, read-only Hub TLS mounts, and no host publication for 8443.
- `infra/jupyter/hub/lakehouse_spawner.py` and `infra/jupyter/hub/lakehouse_policy.py` for read-only CA mount composition and subnet/broker settings, without changing home or data-access isolation semantics.
- New `scripts/prepare-jupyterhub-broker-certificates.py` and a network/subnet preflight helper under `scripts/` (or one cohesive helper) for idempotent cert issuance, validation, and explicit rotation.
- `scripts/prepare-lakehouse-runtime.py`, `scripts/validate-jupyterhub-credentials.py`, `scripts/lakehouse.sh`, `.env.example`, and `.gitignore` as necessary to integrate prerequisites safely.
- New focused test sources under `tests/jupyterhub/` for token ownership/binding, reuse/refresh/rotation races, ambiguous timeout and fail-closed behavior, TLS validation, Spark handoff, safe diagnostics, and network/certificate bootstrap contracts.
- `README.md` for operator commands, broker TLS trust, certificate rotation, and safe Spark launch usage.

Do not create code or configuration under `aidlc-docs/`; that directory holds design/review documents only. Do not change Keycloak claims, Polaris grants, RustFS buckets, existing provider data, or unrelated deferred services.

## Ordered generation steps

### Step 1 — Confirm pinned API compatibility and exact interfaces

- [x] Verify the pinned JupyterHub/Tornado extension hooks for adding a dedicated in-process HTTPS listener and route without altering the browser listener.
- [x] Verify Hub API token validation and user/server lookup behavior for the pinned release; document the authoritative Hub API/state calls used.
- [x] Verify supported auth-state read/update calls and GenericOAuthenticator refresh behavior for the pinned OAuthenticator version.
- [x] Verify the pinned Spark/Iceberg REST client accepts the exact access JWT through an in-memory catalog setting; confirm configuration is not persisted to home files.
- [x] Keep exact transitive dependency pins and existing image digests; add no dependency unless required for the approved design.

### Step 2 — Implement internal TLS broker listener and route

- [x] Add `infra/jupyter/hub/lakehouse_token_broker.py` with a narrow token endpoint and bounded request/response contract.
- [x] Validate the requesting server API token against Hub-owned state and resolve its exact active user/server; reject stopped, absent, mismatched, or invalid bindings.
- [x] Ignore caller-supplied usernames, subjects, roles, groups, and server identifiers for authorization.
- [x] Start the dedicated HTTPS listener in the Hub process on the configured stable `jupyter-user` address and port 8443; register only the broker route and minimal readiness behavior.
- [x] Configure strict request-size/time bounds and safe errors with correlation ID; never include upstream response bodies or credentials.

### Step 3 — Implement same-user token freshness and refresh coordination

- [x] Read only the caller's encrypted Hub auth state and return a reusable access JWT only if more than 60 seconds remain.
- [x] Use a per-stable-user asynchronous lock, with idle-lock cleanup; after acquiring it, reread auth state before contacting Keycloak.
- [x] Refresh only the same user's token using the Hub-held confidential OIDC client secret and refresh token; set a hard five-second timeout and disable automatic replay/retry.
- [x] Persist the successful rotated token set encrypted before releasing waiting callers.
- [x] After an ambiguous timeout, reread auth state exactly once; require reauthentication and deny Spark startup if no sufficiently valid token exists.
- [x] Return only the access JWT and expiry metadata; never return refresh token, ID token, client secret, Hub server token, or role values.

### Step 4 — Add safe logs, counters, and broker readiness

- [x] Record structured correlation ID, permitted validated user/server identifier, decision class, bounded outcome, and elapsed time.
- [x] Add process-local aggregate counters for request count, latency, outcomes, and reuse/refresh decision; no identity/high-cardinality labels.
- [x] Redact authorization headers, JWTs, refresh tokens, client secrets, Keycloak response bodies, and notebook data from exceptions and logs.
- [x] Make Hub readiness fail when certificate validation or listener binding fails; retain existing browser `/hub/health` behavior and ensure readiness also covers broker listener availability.

### Step 5 — Implement host-side certificate and network preparation

- [x] Add idempotent certificate preparation for `.runtime/credentials/jupyterhub-broker-ca-key.pem`, `.runtime/credentials/jupyterhub-broker-server.crt`, `.runtime/credentials/jupyterhub-broker-server-key.pem`, and `.runtime/container-mounts/jupyterhub-broker-ca.crt`.
- [x] Generate/preserve CA identity; never overwrite valid material in routine preparation, never print key data, and never mount the CA signing key.
- [x] Validate file type/mode, certificate chain, `DNS:jupyterhub` SAN, expiry, and server key/certificate match before Hub startup.
- [x] Provide explicit rotation behavior; CA replacement must require an intentional trust-bundle update and user-server recreation.
- [x] Add subnet preflight for `JUPYTER_USER_SUBNET` and stable Hub address, checking host/VPN routes and existing Docker networks before Compose applies IPAM; fail with actionable guidance on overlap.

### Step 6 — Integrate Compose and per-user CA trust

- [x] Update `docker-compose.yml` with configurable `jupyter-user` IPAM, stable Hub `ipv4_address`, internal broker address/port settings, and read-only Hub server cert/key mounts.
- [x] Do not publish port 8443 on host; retain only the existing loopback browser port 8000.
- [x] Update `.env.example` with subnet, Hub address, internal port, and certificate path variables without secret values.
- [x] Update DockerSpawner to add a read-only public CA certificate mount without replacing the per-user home volume or disturbing `data-access` attachment.
- [x] Configure the Spark broker client to call `https://jupyterhub:8443` with explicit CA trust and hostname verification.
- [x] Keep the Hub as the only Docker socket owner; preserve all network and credential isolation requirements.

### Step 7 — Implement Spark session token handoff

- [x] Add `lakehouse_broker_client.py` to call the broker with the server's Hub API token only in an HTTPS authorization header and enforce response schema/expiry.
- [x] Add `lakehouse_spark.py` as the supported session factory: acquire token before each new Spark session and set the exact JWT on the Polaris Iceberg REST catalog in memory.
- [x] Ensure no token is written to arguments, shell history, logs, notebook output, environment dumps, Spark event logs, persistent config, or user-home files.
- [x] Fail Spark startup on TLS, broker, malformed response, insufficient expiry, refresh, or authorization errors; never use a shared service identity or static token.
- [x] Preserve running-session identity; do not silently refresh or switch identity mid-session.

### Step 8 — Add focused Unit 2 test sources

- [x] Add Hub broker tests for invalid/expired server tokens, cross-user attempts, stopped servers, ignored caller identity fields, and safe error responses.
- [x] Add token lifecycle tests for >60-second reuse, refresh, same-user single-flight/re-read, different-user concurrency, timeout without replay, persisted-rotation detection, and fail-closed reauthentication.
- [x] Add certificate/client tests for SAN and CA validation, invalid/missing files, expiry, key mismatch, safe permissions, idempotent preparation, and explicit rotation semantics.
- [x] Add Spark handoff tests proving the exact access JWT is used, only in memory, with no refresh/client token exposure.
- [x] Add subnet conflict and read-only CA mount contract checks.
- [x] Keep tests source-only in Code Generation; execution belongs to Build and Test.

### Step 9 — Update operator documentation and traceability

- [x] Document certificate/subnet preparation before Compose, internal endpoint behavior, CA trust, explicit rotation/restart, and troubleshooting.
- [x] Document the Spark session factory and secure token lifecycle; distinguish user access JWT from Hub API token and refresh token.
- [x] Record US-03, US-06, FR-3, FR-4 client handoff, FR-7 and relevant NFR traceability in the Unit 2 code summary.
- [x] State that Polaris RBAC and RustFS credential vending are Unit 3, and integrated role-matrix/E2E verification is Unit 4.

## Code Generation completion gate

- [x] Approved Unit 2 implementation targets and source-only tests are generated and documented.
- [x] No Unit 2 tests or image builds were executed during Code Generation.
- [x] No runtime containers, provider identities/policies, buckets, catalogs, or data were changed.
- [x] Build and Test is the next stage; integrated token-to-Polaris behavior remains unverified until then.

This plan approval authorized the listed Unit 2 code and test-source work. It does not authorize Unit 3 Polaris/RustFS policy changes, data deletion, or public exposure.
