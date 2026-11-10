# Unit 2 Logical Components — NFR Design

## Logical component inventory

| Component | State / responsibility | Protection and lifecycle |
|---|---|---|
| Hub process and broker TLS listener | Hosts the in-process broker handler on a dedicated internal HTTPS listener; serves requests from isolated user servers. | Listener bound only to the user-server Docker network. Browser ingress and the existing Hub API listener remain separate. |
| Broker request authenticator | Validates the requesting server's Hub API token and resolves its owning user/server from Hub state. | Rejects invalid, stopped, or mismatched bindings; ignores caller-supplied identity and role fields. |
| Token freshness and refresh coordinator | Reads the bound user's OIDC auth state, reuses tokens with more than 60 seconds remaining, or coordinates refresh. | Async lock per stable user identity; rereads state after lock acquisition; no distributed lock. |
| Encrypted Hub auth-state store | Persists each user's access/refresh token set and expiry data. | Encrypted Hub-owned state; not mounted in user servers. Updated token state is persisted before waiters proceed. |
| Keycloak token endpoint | Refreshes the same user's token set when required. | Hub-only outbound call with a 5-second timeout and no automatic replay. Failure results in a safe denial. |
| Internal CA and certificate preparation | Issues the Hub TLS server certificate with the broker DNS name in SAN and prepares trust material. | CA private key remains on the protected host and is never mounted into a container. Rotation is explicit. |
| Hub listener certificate/key | Enables server-authenticated HTTPS for the broker endpoint. | Read-only mount into Hub; private key is inaccessible to user servers. |
| User-server CA trust material | Allows the Spark launcher/client to validate the Hub certificate and broker DNS identity. | Public CA certificate only, read-only in the user runtime or pinned image. TLS verification is mandatory. |
| Spark launcher and Polaris REST client | Calls broker before session startup, validates response, then configures the exact user JWT in memory. | No token in command line, logs, notebook output, persistent configuration, or home files. No refresh token is returned. |
| Token-safe diagnostics | Captures correlation, validated identity/server where allowed, decision class, safe outcome, timing, and aggregate counters. | Structured Hub logs and process-local counters only; bounded labels, no bearer material, no user-server-reachable metrics endpoint. |

## Request and refresh flow

```mermaid
sequenceDiagram
  participant S as User server / Spark launcher
  participant T as Internal HTTPS broker listener
  participant B as Hub broker and request authenticator
  participant A as Encrypted Hub auth state
  participant K as Keycloak token endpoint
  participant P as Polaris REST API
  S->>T: HTTPS request + Hub server API token
  T->>B: Authenticated broker request
  B->>B: Resolve user/server from Hub state
  B->>A: Read bound user's token state
  alt Access JWT has >60 seconds remaining
    A-->>B: Current access JWT and expiry
  else Refresh required
    B->>B: Acquire per-user async lock; reread state
    B->>K: Refresh, timeout 5 seconds, no replay
    K-->>B: Rotated token response
    B->>A: Persist updated encrypted auth state
  end
  B-->>S: Access JWT and expiry only
  S->>S: Configure Spark in memory
  S->>P: Polaris REST request with exact user's Bearer JWT
```

## Trust and network boundaries

- **Hub control plane:** owns Hub API-token validation, encrypted auth state, OAuth client secret, CA issuance key on protected host, Hub listener private key, and Docker control-plane capability.
- **User runtime:** receives only its own Hub server credential and the returned user access JWT; validates broker TLS with the public CA certificate. It cannot read Hub state, refresh tokens, OAuth secret, CA private key, Docker Engine, or another user's home.
- **Keycloak boundary:** reachable from the Hub for authentication/refresh. User servers do not receive direct Keycloak access for this broker flow.
- **Data access:** Spark uses the user JWT to call Polaris. Unit 3 defines Polaris RBAC and RustFS credential vending; Unit 2 does not grant storage credentials.
- **Browser ingress:** existing loopback HTTP route remains unchanged and is distinct from the internal broker TLS listener.

## Failure behavior

1. Missing or invalid caller server token, stopped/mismatched server, or failed admission check returns a safe denial; no user identity is inferred from request fields.
2. Missing/decryption-failed Hub auth state or unavailable Keycloak prevents a new Spark session.
3. On refresh timeout, the coordinator rereads state once and never resubmits the potentially rotated refresh token. If no valid refreshed access token exists, it requires reauthentication.
4. A malformed broker response or insufficient remaining token lifetime is rejected by the launcher; Spark is not started.
5. Diagnostics retain only correlation and safe outcome metadata, without authorization headers, token values, response bodies, or notebook data.

## Deployment decisions deferred

Unit 2 Infrastructure Design selects the concrete internal listener port and route wiring, broker DNS name, TLS preparation command and file paths, Compose bind/mount declarations, and restart/rotation procedure. These choices must preserve the network and credential boundaries above.
