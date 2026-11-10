# Component Methods — JupyterHub User Access

These are logical contracts, not implementation signatures. Construction will bind them to the exact JupyterHub and Keycloak client versions selected for the runtime.

| Component | Method / operation | Inputs | Output | Purpose |
|---|---|---|---|---|
| OIDC authenticator | `begin_login(request)` | Browser request, configured realm/client, callback URI | Redirect to Keycloak with state, nonce, and Authorization Code parameters | Starts browser-based OIDC login; never requests a user's password directly. |
| OIDC authenticator | `complete_login(request)` | OIDC callback code and state | Authenticated Hub user plus encrypted auth state, or a fail-closed denial | Validates callback, obtains tokens, resolves identity and approved group membership. |
| OIDC authenticator | `get_handlers()` | Hub application context | Registered Hub-side broker handler(s) | Adds the broker route through the pinned Authenticator extension contract. Verify exact compatibility during construction. |
| OIDC authenticator | `persist_auth_state(user, token_set)` | Hub user, access/refresh token set, expiry metadata | Encrypted Hub auth-state record | Retains only the Hub-side token material needed for per-user refresh. |
| Spawner | `prepare_user_server(user, auth_state)` | Authenticated Hub user and that user's auth state | User-specific container configuration and isolated named home volume | Applies admission result and configures one isolated single-user server. |
| Spawner | `start(user, server_config)` | User identity, image/resources, volume, runtime-only access JWT | Running server URL and lifecycle metadata | Starts the user's Jupyter/Spark container; Docker API access remains on the Hub side. |
| Broker handler | `issue_spark_access_token(hub_server_token)` | Bearer Hub API token from the calling single-user server | `{access_token, expires_at}` for that server's authenticated user, or denial | Authenticates the server token, derives the Hub user/server binding, refreshes only its encrypted auth state, and returns only the current access JWT. |
| Broker handler | `refresh_user_session(user_id)` | User identity derived from verified Hub server model | Updated encrypted auth state or fail-closed error | Uses the Hub's confidential Keycloak client to refresh that same user's session. Never accepts caller-supplied identity as authority. |
| Spark launcher | `start_session(configuration)` | Spark/Iceberg configuration and broker URL | Spark local session with runtime-only user JWT | Requests a fresh token immediately before Spark creation and passes the exact JWT through the configured Polaris bearer-token property. |
| Spark client | `catalog_request(request, access_token)` | Iceberg REST operation and user access JWT | Polaris response or authorization failure | Sends `Authorization: Bearer <user JWT>` to the selected Polaris realm/catalog endpoint. |
| Polaris | `validate_and_map_token(jwt)` | JWT, configured realm and OIDC mappings | Verified principal and allowed role set, or rejection | Enforces signature, canonical issuer, expiry, `polaris` audience, username, and allow-listed role claims. |
| Polaris | `authorize_catalog_operation(principal, roles, operation, location)` | Verified identity, roles, requested operation and resource | Allow/deny | Applies existing internal Polaris grants for developer or analyst access. |
| Polaris | `vend_storage_credentials(principal, authorized_location)` | Authorized operation and storage location | Temporary scoped RustFS credential set | Enables the client to access only the authorized object-store location. |
| User Spark runtime | `access_iceberg_data(catalog, operation)` | Catalog/table and current Spark session | Iceberg result or explicit failure | Uses Polaris REST for metadata and Polaris-vended temporary credentials for direct RustFS I/O. |

## Error contract

- Invalid OIDC state, failed group admission, invalid Hub server token, cross-user binding, Keycloak refresh failure, invalid/expired JWT, missing audience/role, Polaris denial, or storage credential failure is an explicit failure. No shared writer identity or root RustFS fallback is permitted.
- User-facing/logged error context may include correlation ID, authenticated username after validation, component, and failure class. It must exclude access tokens, refresh tokens, client secrets, and temporary storage secret values.
- If a Spark session's JWT expires during execution, authenticated Polaris requests can fail. A new Spark session obtains a fresh token; a running Spark session does not silently swap identity.
