# Unit 2 Business Logic Model — Hub Token Broker and Spark Session Identity

## Actors and outcome

- **User** requests a Spark session from their own Jupyter server.
- **Single-user server** calls the Hub broker with its Hub-issued API token, then configures Spark with the returned access JWT in memory.
- **Hub broker** authenticates the server token, derives the bound Hub user/server, reads and refreshes that user's encrypted OIDC state, and returns only the current access token.
- **Keycloak** refreshes the same user's token set when the access token is expired or too close to expiry.
- **Polaris** receives the exact user's access JWT as a Bearer token from Spark; validation and authorization are Unit 3.

The successful outcome is a Spark session configured with the same user's current access JWT. No refresh token, client secret, or alternate identity reaches the user runtime. An identity-binding or refresh failure prevents Spark session creation.

## Broker request and identity binding

1. The launcher requests a token immediately before creating each Spark session.
2. It sends a broker request over the Hub-to-user network path and authenticates only with its own Hub API token in the authorization header.
3. The broker validates the token against Hub-owned state and resolves the exact user and server associated with it. Caller-supplied username, subject, roles, or server identifiers do not affect identity resolution.
4. The broker confirms that the resolved Hub session and server are active and that current Hub admission state remains eligible. If a Keycloak refresh is required, refreshed role/group claims must still satisfy Unit 1 admission. Group changes are observed only when Hub/Keycloak state is revalidated or refreshed; instant group-revocation detection is not promised, and Unit 1's operator stop fallback still applies.
5. The broker reads only that user's encrypted OAuth auth state; it does not use another user's state or a shared service identity.

## Token selection and refresh workflow

1. If the stored access token has more than 60 seconds remaining, return it with its expiry.
2. If it is expired or has 60 seconds or less remaining, acquire a per-user refresh lock.
3. After acquiring the lock, re-read that user's auth state. If another concurrent request has already refreshed it and it now has more than 60 seconds remaining, reuse that token without a second refresh.
4. Otherwise, use the Hub-held refresh token with Keycloak to refresh only that user's session. Persist the updated encrypted token state before releasing the lock.
5. Waiting requests for the same user reuse the successfully refreshed state. Different users have isolated locks and token state.
6. If refresh fails, auth state is absent/revoked, or the resulting token is invalid or too near expiry to use safely, deny new session startup. Do not return an expired or stale token.

```mermaid
sequenceDiagram
  participant L as Spark launcher
  participant B as Hub broker
  participant H as Hub auth state
  participant K as Keycloak
  L->>B: Request token with Hub server API token
  B->>B: Validate token; derive user/server from Hub state
  B->>H: Read only bound user's encrypted auth state
  alt Access token has >60 seconds remaining
    H-->>B: Current access token and expiry
  else Expired or <=60 seconds remaining
    B->>B: Acquire per-user refresh lock
    B->>H: Re-read state after lock
    alt Concurrent request already refreshed
      H-->>B: New current access token
    else Refresh still needed
      B->>K: Refresh same user's token set
      K-->>B: Updated token set
      B->>H: Persist encrypted updated state
    end
  end
  B-->>L: Access token and expiry only
  L->>L: Configure Spark in memory with exact Bearer JWT
```

## Spark handoff

- The launcher calls the broker for every new Spark session; it does not use a token saved in a notebook, home file, shell history, process argument, or prior Spark configuration.
- The response contains only the current access token and expiry metadata. The refresh token is never returned.
- The launcher validates response shape and remaining lifetime before Spark starts.
- The exact access JWT is passed in memory to the Spark Iceberg REST catalog client as the Polaris Bearer token. It is not printed or persisted.
- A running Spark session retains the identity established at its start. If its JWT expires, subsequent authenticated Polaris operations may fail. The session does not silently refresh or switch identity; a new Spark session obtains a new token.

## Failure paths

| Condition | Functional result |
|---|---|
| Missing, malformed, expired, or revoked Hub API token | Deny broker request; do not reveal another user's/server's existence. |
| Caller supplies another username, subject, role, or server | Ignore for authorization; derive identity only from validated Hub token state. |
| Bound Hub user/server is stopped, missing, or known to be ineligible at current Hub/Keycloak revalidation | Deny token issuance and new Spark startup. |
| User auth state is absent, unreadable, or cannot be decrypted | Deny; do not use a cached shared identity. |
| Keycloak is unavailable or refresh token is expired/revoked | Deny new Spark session; provide safe diagnostics without token material. |
| Concurrent same-user refresh | Serialize; re-read after lock and use the first valid refreshed state. |
| Broker response is malformed or token lifetime insufficient | Launcher rejects it and does not start Spark. |
| Polaris rejects or expires the token during a running Spark session | Surface a safe operation failure; require a new Spark session for a fresh token. |

## Audit and observability

Record correlation ID, validated Hub user/server, token decision class (reused/refreshed/denied), and failure category. Never log request authorization headers, access or refresh JWTs, client secrets, or token endpoint response bodies. Do not place tokens in notebook output or exception text.

## Scope handoff

Unit 2 ends when the broker safely issues the requesting server's current user token and Spark uses that exact JWT for Polaris REST. Unit 3 owns Polaris claim validation, authorization, and RustFS credential vending. Unit 4 owns integrated developer/analyst verification.
