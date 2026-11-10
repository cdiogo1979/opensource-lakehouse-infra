# Unit 2 Business Rules — Hub Token Broker and Spark Session Identity

## Broker authentication and identity

1. Every broker request must present the requesting single-user server's Hub API token in the authorization header.
2. The Hub validates the token and derives the associated user and server from Hub-owned records. Request parameters and headers cannot override that binding.
3. A server token can obtain only its own Hub user's current access JWT. Cross-user and cross-server requests fail closed.
4. A stopped, missing, revoked, or known-ineligible Hub user/server cannot obtain a token for a new Spark session. On refresh, current Keycloak role/group claims must still satisfy Unit 1 admission. Group removals take effect when observed at Hub/Keycloak revalidation or refresh; instant revocation is not promised, and Unit 1's operator stop fallback applies to running servers.

## Token lifecycle

1. Request a broker token before each Spark session.
2. Reuse the current access token only when more than 60 seconds remain before expiry. Refresh an expired token or one with 60 seconds or less remaining.
3. Serialize refresh attempts by Hub user. After acquiring the lock, re-read encrypted auth state; reuse it if another request has already refreshed it.
4. Use only the bound user's refresh token, retained in encrypted Hub auth state. Persist a successful rotated token set before releasing waiting callers.
5. Return only the access JWT and expiry metadata. Never return refresh tokens, client secrets, ID tokens, roles as authorization inputs, or Hub API tokens.
6. A failed, revoked, expired, or unverifiable refresh denies new Spark startup. Do not fall back to an older expired token, a shared writer identity, or a long-lived credential.
7. A running Spark session does not silently change identity. If its JWT expires, authenticated operations may fail; a new session must request a new token.

## Spark handoff and confidentiality

1. Use the exact broker-issued access JWT as the Polaris Bearer token for that Spark session.
2. Keep the JWT in runtime memory/configuration only. Do not write it to command arguments, shell history, notebook output, user-home files, persistent Spark configuration, image layers, or logs.
3. Do not expose the Hub OAuth client secret or any user's refresh token to a single-user server.
4. Validate the broker response shape and expiry before constructing Spark. Missing, malformed, or too-short-lived credentials prevent startup.

## Failure and audit

- Fail closed for invalid Hub tokens, missing/mismatched server binding, inactive or ineligible user state, auth-state read/decryption failure, Keycloak outages, refresh failures, malformed responses, and token expiry.
- Return safe error categories and a correlation identifier; do not reveal token values, refresh response bodies, or whether another user's state exists.
- Audit only validated identity, server ID, decision class, and failure category. Never log bearer tokens or client secrets.
- Unit 2 does not decide Polaris grants, role-claim validation, or RustFS storage scope; Unit 3 owns those policies.
