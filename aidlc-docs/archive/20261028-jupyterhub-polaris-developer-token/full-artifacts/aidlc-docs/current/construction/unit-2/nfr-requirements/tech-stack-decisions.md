# Unit 2 Technology Decisions — Hub Token Broker and Spark Session Identity

## Decisions

| Concern | Decision | Rationale / constraint |
|---|---|---|
| Broker location | In-process JupyterHub extension/handler | Matches approved application design; no additional service or credentials plane. |
| Caller authentication | Hub-issued per-server API token in an HTTPS authorization header | Allows Hub to derive server and user from its own state; caller identity fields are not trusted. |
| Broker transport | Internal HTTPS with certificate verification from each user container | Protects bearer credentials on the shared Docker bridge. This does not change the separately approved loopback browser-ingress scheme. |
| Auth state | Existing encrypted JupyterHub auth state | Refresh token and confidential-client secret remain Hub-side; no new persistence system. |
| Access-token freshness | Reuse only when more than 60 seconds remain; refresh otherwise | Avoids unnecessary refresh exchanges while preserving startup headroom. |
| Refresh coordination | Per-user in-process asynchronous lock and state re-read after lock | One Hub process is supported. It prevents same-user refresh-token races while allowing different users concurrently. |
| Keycloak refresh timeout | 5 seconds; no automatic replay | Refresh token rotation makes a timeout outcome ambiguous. Re-read Hub state once, then fail closed and require reauthentication if no valid updated token exists. |
| Spark token handoff | Return only access token and expiry; configure Spark in memory | Exact same-user JWT reaches Polaris without exposing refresh tokens or persisting bearer values. |
| Observability | Aggregate counters/timing and safe structured outcome records | Supports operations while excluding bearer credentials and sensitive metric labels. |

## Implementation constraints

- Preserve the canonical Keycloak issuer and use the approved back-channel endpoint behavior; do not substitute a service account for the user.
- The certificate must include the broker's internal service name and be trusted by the user image. Certificate private keys remain Hub-only; distribute only trust material to user images/containers.
- Do not add Redis or another coordination service for the approved single-Hub profile. If Hub becomes multi-replica, replace the process-local lock before scaling.
- No token may appear in environment dumps, process command lines, logs, notebooks, or persistent home/configuration files.
- Polaris REST token validation and RustFS credential vending are Unit 3 decisions; end-to-end role/access acceptance is Unit 4.

## Deferred to Infrastructure Design

Unit 2 Infrastructure Design must select the internal TLS listener implementation, internal broker DNS name and port, certificate generation/storage/rotation, and how the CA trust certificate reaches user containers without changing the approved browser-facing local ingress.
