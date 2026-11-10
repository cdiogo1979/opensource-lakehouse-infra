# Unit 2 Infrastructure Design — Hub Token Broker and Spark Session Identity

## Scope

This design maps the approved Unit 2 Hub broker and NFR design to the existing local Compose deployment. It adds an internal HTTPS listener and certificate material to the existing Hub/user-server path. It does not add a service, database, queue, host-published broker port, metrics endpoint, or modify browser ingress.

## Service and network mapping

| Logical component | Infrastructure mapping | Configuration and lifecycle |
|---|---|---|
| Hub broker listener | Additional TLS listener in the existing `jupyterhub` container/process on port `8443`. | Bind to the Hub's stable address on `jupyter-user`; publish no host port. User servers call `https://jupyterhub:8443`. Keep `http://jupyterhub.localhost:${JUPYTERHUB_HOST_PORT:-8000}` as the separate loopback browser endpoint. |
| Hub user-network address | Explicit Docker bridge IPAM configuration for `jupyter-user`; assign the Hub a stable address and leave spawned user addresses dynamic. | Expose subnet and Hub address as Compose environment settings. Default example: `172.30.240.0/24`, Hub `172.30.240.10`; preflight checks host/VPN routes and existing Docker networks for overlap before Compose applies IPAM. Operator may override on collision. |
| User servers | Existing DockerSpawner containers on `jupyter-user` and `data-access`. | Continue using service DNS for the Hub broker and Polaris/RustFS on `data-access`. No `core` attachment, Docker socket, Hub DB, Keycloak, PostgreSQL, or administrative secrets. |
| Broker TLS trust | User-server DockerSpawner read-only bind mount for the public CA certificate. | Mount only `.runtime/container-mounts/jupyterhub-broker-ca.crt` to `/run/certs/jupyterhub-broker-ca.crt`; configure the broker HTTP client with this CA bundle and verify the `jupyterhub` hostname. Do not disable TLS verification. |
| Safe metrics and logs | In-process Hub counters and structured Hub logs. | No metrics listener, Prometheus service, or external logging backend. Counters reset on Hub restart; safe structured logs retain the diagnostic record. |

### Compose network membership

Preserve the Unit 1 network boundary:

```text
core:          Keycloak, provider databases, Polaris, RustFS, JupyterHub
jupyter-user:  JupyterHub at stable internal IP, each spawned user server
data-access:   Polaris, RustFS, each spawned user server
```

The Hub broker binds only to its `jupyter-user` interface address, so services connected to `core` cannot reach port 8443 through the Hub's other interface. The Hub's existing browser/Hub API listener remains separately configured and only its existing browser port is published on host loopback. The Hub still uses the Docker API to spawn servers and attach them to `data-access`; user servers do not receive Docker API access.

The `jupyter-user` subnet must be checked against host, VPN, and Docker network routes before startup. If the default example overlaps, change the configured subnet and Hub address together. Use the Hub's service DNS name (`jupyterhub`) for the TLS hostname; the certificate SAN and client verification name must match.

## Certificate storage and mount map

| Host path | Material | Container access |
|---|---|---|
| `.runtime/credentials/jupyterhub-broker-ca-key.pem` | Internal CA private signing key | Host only; mode `0600`; never mounted into a container. |
| `.runtime/credentials/jupyterhub-broker-server.crt` | Hub broker server certificate with `DNS:jupyterhub` SAN | Read-only mount into Hub. |
| `.runtime/credentials/jupyterhub-broker-server-key.pem` | Hub broker server private key | Read-only mount into Hub; restrictive host mode `0600`, container process-readable only. Never mounted into user servers. |
| `.runtime/container-mounts/jupyterhub-broker-ca.crt` | Public internal CA certificate | Read-only mount into spawned user servers at `/run/certs/jupyterhub-broker-ca.crt`. This is trust material, not a signing credential. |

All `.runtime` material remains ignored by version control. Runtime preparation creates directories/files with restrictive permissions, is idempotent, preserves existing CA identity, and does not print private key contents. It validates the server certificate chain, SAN, validity period, key match, and permissions before the Hub starts its TLS listener.

## Startup and rotation procedure

1. Run the idempotent host-side broker certificate preparation command before Compose startup. Missing material is generated once; existing valid material is preserved.
2. Run a network preflight that checks the configured `jupyter-user` subnet for overlap with local routes and Docker networks. Stop with an actionable error on conflict; do not silently pick another subnet that would invalidate the Hub address.
3. Start Compose. The Hub loads the read-only server cert/key, binds its broker TLS listener to the configured `jupyter-user` address on `8443`, and reports unhealthy/fails startup if TLS material or the listener is invalid.
4. Spawned servers receive the read-only public CA certificate and use it for hostname-validating HTTPS calls to `https://jupyterhub:8443`.
5. For rotation, run an explicit operator command that issues replacement certificate material using the existing CA. Recreate the Hub and affected user servers so mounts are refreshed, then verify the TLS chain and SAN from a user-server network context. CA replacement itself requires a deliberate trust-bundle update and recreation; there is no automatic certificate or trust fallback.

The Hub health check must include local broker-listener readiness (or an equivalent in-process readiness flag) as well as the existing `/hub/health` check. Missing/invalid TLS setup prevents readiness rather than downgrading to HTTP.

## Broker request path and credentials

1. The launcher sends a request to `https://jupyterhub:8443` with its Hub-issued server API token in the authorization header.
2. The listener validates TLS and passes the request to the in-process broker handler. The handler resolves user/server binding from Hub-owned state; caller identity fields are ignored.
3. Reuse a user's access JWT only if more than 60 seconds remain. Otherwise serialize refresh by stable Hub identity, reread encrypted auth state after acquiring the lock, and call Keycloak from the Hub with a five-second timeout and no automatic replay.
4. Persist successful refreshed auth state before returning. On timeout, reread state once, then fail closed if no valid token exists.
5. Return only the exact user's access token and expiry. Spark configures Polaris REST auth in memory; no token enters command arguments, environment dumps, logs, user homes, notebook output, or persistent Spark configuration.

## Observability and operations

- Record correlation ID, permitted validated user/server identifiers, decision (`reused`, `refreshed`, or `denied`), bounded outcome class, and elapsed time in structured Hub logs.
- Maintain process-local aggregate request, latency, outcome, and token-decision counters. Avoid high-cardinality or identity labels; counters reset on Hub restart.
- Do not add a reachable metrics endpoint, monitoring container, queue, or database.
- Never log authorization headers, access/refresh tokens, OAuth secrets, Keycloak response bodies, notebook contents, or storage credentials.

## Capacity, failure, and limits

- Reuse and refresh targets remain 2 seconds and 5 seconds under normal local conditions; the Keycloak request timeout is 5 seconds. Later tests must measure these targets; this design is not evidence of performance results.
- Two different users may call concurrently. Same-user refreshes serialize with one process-local async lock per user. No distributed lock or multi-Hub scaling is supported.
- Invalid TLS, missing trust material, invalid Hub API token, server mismatch, unavailable Keycloak, invalid auth state, or inadequate token expiry prevents new Spark startup. Never fall back to HTTP, stale JWT, or service credentials.
- The design remains local-only and single-Hub. It provides no public ingress TLS, host egress filtering, HA, immediate group-revocation detection, or production SLA.

## Deferred to Code Generation and Build and Test

Code Generation will implement the additional listener and handler, certificate preparation/preflight/rotation helpers, Compose IPAM and read-only mounts, DockerSpawner CA mount, client trust configuration, readiness integration, and focused tests. Build and Test must verify subnet conflict handling, TLS SAN/chain verification from a spawned user server, denial when trust is invalid, broker token confidentiality, two-user concurrency, timeout behavior, and latency targets. Existing running containers and runtime files are not modified by this design artifact.
