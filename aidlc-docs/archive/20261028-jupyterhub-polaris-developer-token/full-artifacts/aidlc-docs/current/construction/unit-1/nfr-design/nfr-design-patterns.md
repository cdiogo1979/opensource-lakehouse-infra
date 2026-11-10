# Unit 1 NFR Design Patterns — JupyterHub Foundation

## Scope and targets

This design is for a local, single-node Compose deployment with one Hub and up to two concurrent user servers. It has no uptime SLA, HA, or automated backup requirement. The measurable targets are Hub callback processing within 5 seconds after callback receipt and server readiness within 120 seconds under recorded local host/image conditions.

## Capacity and resource isolation

- Run one Hub process and support two simultaneous single-user containers.
- Configure per-user CPU and memory limits as host-tunable settings. Select concrete values during Infrastructure Design after checking the supported machine; the two-server acceptance test validates that both limits fit together.
- Do not introduce autoscaling, queues, shared Spark executors, or multi-host scheduling for this local profile.
- Preserve the one-user/one-container/one-home isolation boundary. User containers never receive Docker Engine access.

## Spawn performance

- Build or pull the exact pinned Hub and matching Spark-enabled single-user images before the user starts a server. Do not include image build or cold registry pull in the interactive spawn path.
- Keep single-user startup deterministic and limited to runtime initialization. Heavy package resolution and downloads belong in image build, not server start.
- Record callback-receipt, login-response, spawn-request, and ready timestamps using safe correlation IDs. Exclude Keycloak user-interaction time from callback processing.
- Validate the 5-second callback and 120-second ready targets on the supported local host with the two-user capacity configuration. Report host and image conditions with results.

## Persistence pattern

- Store JupyterHub SQLite state, including encrypted auth state and Hub-managed server state, on a dedicated named Hub state volume.
- Keep the Hub crypt key and confidential OIDC client secret in protected runtime credentials, mounted read-only into Hub and separate from the SQLite volume and user homes.
- Keep each user's notebooks/files on a separate persistent named volume keyed to the stable Hub identity. Stop/restart and failed spawn preserve the volume.
- Normal Compose/service restart preserves volumes. Explicit volume removal, local disk failure, and disaster recovery are outside the guarantee.
- Operator-managed backups, when desired, must capture the Hub database and corresponding crypt key together with user homes. Automated backup/restore is not added.

## Resilience and recovery

- Fail closed when Keycloak is unavailable during login or admission, when OIDC state/identity validation fails, or when auth state cannot be persisted.
- Do not auto-retry a failed spawn. Clean partially created user server/container resources, preserve the user's home, report a safe failure class, and wait for a deliberate user/operator retry.
- Make spawn cleanup idempotent so a retry cannot attach to an orphaned container or another user's home.
- If group membership is removed, stop a running server at the next admission/auth-state revalidation. Where no revalidation event occurs, an operator must stop it; do not imply immediate revocation.
- Hub restart may interrupt active sessions. After restart, load persistent state and allow eligible users to start again; do not assume a server is healthy solely because a DB record says it was running.

## Security and privacy patterns

- Use the approved OIDC Authorization Code flow with state/nonce checks and approved-group admission. The local profile remains loopback HTTP only.
- Encrypt Hub auth state at rest with a separately protected crypt key. Do not expose refresh tokens or the OIDC client secret to single-user containers.
- Give Docker Engine API access only to the Hub control plane. Do not mount the Docker socket or Hub state volume into user containers.
- Keep JWTs and secrets out of logs, metrics, command lines, home volumes, image layers, and notebook outputs. Emit safe identity, lifecycle, duration, correlation, and error-category fields only.
- Do not expand the declined broader security baseline. Production TLS and shared deployment security require a separate design.

## Observability and operator feedback

- Use service logs with explicit safe categories: OIDC failure, admission denial, auth-state error, spawn failure, stop/revocation, and successful lifecycle transitions.
- Include validated username after successful identity validation and correlation IDs, but redact all bearer tokens, refresh tokens, secrets, and user data.
- Expose Hub/container health through service health checks. A Keycloak outage should cause login/admission failure without causing user identity fallback.
- No external metrics backend, alerting service, tracing collector, queue, cache, or circuit-breaker service is required for two local users.
