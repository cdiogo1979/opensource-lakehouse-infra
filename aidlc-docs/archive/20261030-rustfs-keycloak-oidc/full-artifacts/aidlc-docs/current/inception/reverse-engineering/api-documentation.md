# API Documentation — RustFS OIDC Surface (1.0.4, observed)

Source: identifiers extracted from the running `rustfs/rustfs:1.0.4` binary plus live read-only probes. Semantics below are inferred from names and must be verified during design.

## Configuration (environment)
`RUSTFS_IDENTITY_OPENID_` + `ENABLE`, `CONFIG_URL`, `ISSUER`, `CLIENT_ID`, `CLIENT_SECRET`, `SCOPES`, `OTHER_AUDIENCES`, `REDIRECT_URI`, `REDIRECT_URI_DYNAMIC`, `CLAIM_NAME`, `CLAIM_PREFIX`, `ROLE_POLICY`, `GROUPS_CLAIM`, `ROLES_CLAIM`, `EMAIL_CLAIM`, `USERNAME_CLAIM`, `DISPLAY_NAME`, `HIDE_FROM_UI`.

The same keys exist as `identity_openid` server configuration (`client_id`, `client_secret`, `config_url`, `scopes`, `redirect_uri`, `claim_name`, `role_policy`, ...), suggesting it may also be configurable through the admin API.

## REST endpoints
### List providers
- **Method/Path**: `GET /rustfs/admin/v3/oidc/providers` (port 9000)
- **Observed**: HTTP 200, `[]`, unauthenticated.
### Authorize / callback
- **Paths**: `/rustfs/admin/v3/oidc/authorize/<provider>`, `/rustfs/admin/v3/oidc/callback/<provider>` (a `callback/default` literal exists).
- **Purpose**: Browser Authorization Code login for the console. The browser-facing port (9000 vs 9001) and the exact redirect URI to register are unverified.
### Logout / validate
- **Paths**: `/rustfs/admin/v3/oidc/logout`, `/rustfs/admin/v3/oidc/validate`.
### STS
- **Action**: `AssumeRoleWithWebIdentity` — exchanges an OIDC token for temporary S3 credentials.

## Authorization model (to verify)
OIDC sessions are expected to receive RustFS policies either from a token claim naming canned policies (`CLAIM_NAME`, optionally `CLAIM_PREFIX`) or from a fixed `ROLE_POLICY`. Either way, the named RustFS canned policies must exist. The live canned-policy inventory was not checked (no signing client available on the host); the current repository creates none for the `role-default-*` groups.

## Keycloak side (existing)
- Realm `lakehouse`; issuer `http://keycloak.localhost:8080/realms/lakehouse`; group claim `groups` via `oidc-group-membership-mapper` on per-client basis; principal claim `preferred_username`.
