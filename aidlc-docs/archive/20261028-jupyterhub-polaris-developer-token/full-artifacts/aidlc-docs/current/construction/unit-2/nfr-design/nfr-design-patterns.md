# Unit 2 NFR Design Patterns — Hub Token Broker and Spark Session Identity

## Scope and constraints

This design applies to one local JupyterHub process and at most two active user servers. It covers the Hub-side broker, safe handoff of the requesting user's access JWT to a new local Spark session, and the non-functional patterns around that path. Polaris authorization and RustFS credential vending remain Unit 3; integrated journey verification remains Unit 4.

The approved targets are a broker reuse response within 2 seconds and a normal successful refresh response within 5 seconds. Keycloak refresh calls have a hard 5-second timeout. The broker must not replay an ambiguous refresh, must reread Hub auth state once, and must fail closed when no sufficiently valid token exists.

## Broker endpoint and transport

- Keep the broker as an in-process JupyterHub extension. Run a dedicated TLS listener in the Hub process, bound only to the Docker network used by user servers. The listener serves only the broker route; it does not replace or widen the browser-facing loopback ingress or the existing Hub API listener.
- User servers address the broker by its internal Docker service DNS name. The Hub server certificate contains that exact name in its subject alternative names (SANs). Clients validate the full certificate chain and hostname; verification is never disabled.
- The broker validates the server's Hub-issued API token using Hub-owned records and derives the user/server binding from those records. It accepts no caller-supplied username, subject, group, role, or server identity as authorization input.
- Keep the request and response bearer values in HTTPS authorization/body handling and process memory only. Redact authorization headers, access tokens, refresh tokens, OAuth client secrets, and Keycloak response bodies from all logs and exceptions.
- Preserve the existing network boundary: user servers can reach the broker on the user-server network and Polaris/RustFS on the approved data-access network; they do not gain access to Keycloak, PostgreSQL, Docker Engine, Hub state, or Hub administrative credentials.

## Certificate lifecycle

- A protected runtime-preparation command creates an internal CA and signs the Hub listener certificate. The CA private key is used for issuance and retained only in the protected host runtime credential area with restrictive permissions; it is not mounted into containers.
- Mount the Hub listener certificate and private key read-only into the Hub container. Mount only the CA public certificate read-only into each user server or bake it into the matching pinned user image. Do not distribute the CA signing key to any container.
- Require the user runtime's HTTP client to use the CA certificate and validate the broker DNS name. Startup fails closed if trust material or the server certificate is missing or invalid.
- Certificate rotation is an explicit operator action: issue a replacement certificate, refresh the Hub and user-server trust mounts as needed, then restart the Hub listener and affected user servers. No silent regeneration or automatic trust bypass is allowed.
- Concrete file locations, permissions, Docker mounts, commands, and port numbers are selected in Infrastructure Design.

## Token selection, refresh, and concurrency

- Before each Spark session, the launcher makes one authenticated broker request. If the stored access JWT has more than 60 seconds remaining, the Hub returns it without contacting Keycloak.
- If refresh is required, acquire an asynchronous lock keyed by the stable Hub user identity. Different users use independent locks, preserving the approved two-user concurrency. After acquiring the lock, reread the user's encrypted auth state so queued requests can reuse a token refreshed by the first caller.
- Bound Keycloak's refresh request to 5 seconds. Do not automatically replay the refresh token after a timeout. Reread auth state once to detect persisted rotation; if no sufficiently valid state is available, return a safe denial and require reauthentication.
- Persist successful rotated token state encrypted in Hub state before releasing waiting requests. Retain no raw refresh token outside Hub auth state and the outbound Keycloak exchange.
- Keep the lock registry process-local. Remove idle lock entries when no caller is waiting or holding the lock; with two users, no distributed lock, queue, or cache is justified. A multi-Hub deployment would require a new coordination design before scaling.
- Return only the exact user's access JWT and expiry metadata. Configure the Spark Polaris REST client in memory. Do not place the JWT in environment dumps, arguments, notebook output, persistent Spark configuration, user-home files, or logs.
- A running Spark session does not change identity or refresh its JWT. Expired-token operations may fail; a new Spark session obtains a fresh token.

## Resilience and failure behavior

- Fail closed for invalid or mismatched Hub server tokens, inactive/missing server state, failed current admission checks, unreadable/decryption-failed Hub auth state, Keycloak outage, invalid refresh result, malformed response, or insufficient token lifetime.
- Do not fall back to a stale token, shared service account, or long-lived storage key. No automatic broker retry or refresh replay is introduced.
- Return a bounded safe failure class and correlation ID. Preserve user home and Hub state on broker failure; no Spark session is started.
- The Hub process is a single point of service for the local profile. Restart recovery uses its persistent Hub state and protected crypt key; no HA or uptime guarantee is added.

## Capacity and performance

- Support up to two active user servers and concurrent broker requests from both users. Only same-user refresh work is serialized.
- Apply bounded request handling and the Keycloak timeout. Avoid a global lock and avoid network calls on the token-reuse path.
- Measure reuse and refresh latency separately. Verify the two-second and five-second targets under documented local host conditions in the later test stage; these are requirements, not claimed results.
- Do not add autoscaling, multi-Hub support, distributed coordination, or an external cache for this local profile.

## Observability

- Emit token-safe structured Hub logs containing correlation ID, validated user/server identifiers where permitted by Hub log access, decision class (`reused`, `refreshed`, or `denied`), bounded outcome category, and elapsed time.
- Maintain process-local aggregate counters for request count, latency buckets/summaries, outcome category, and reuse/refresh decision. Counters reset on Hub restart; logs remain the operational record.
- Do not expose a metrics endpoint to the user-server network or add an external metrics backend in this unit. Do not use user, server, token, or correlation identifiers as metric labels.
- Never log authorization headers, JWTs, refresh tokens, client secrets, token endpoint bodies, notebook contents, or other user data.

## Security boundary

- TLS authenticates the Hub broker endpoint and protects Hub API bearer tokens and access JWTs in transit over the shared user-server bridge.
- The Hub remains the only owner of OAuth refresh tokens, confidential-client credentials, encrypted auth state, certificate signing key, and Docker control-plane access.
- Spark receives only the user's access token for its own session. It receives no Hub API token beyond the caller's existing server credential, no refresh token, and no service identity credential.
- Internal broker TLS does not change browser ingress. This design does not claim public TLS, host egress filtering, immediate group-revocation detection, or multi-tenant production hardening.
