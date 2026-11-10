# API Documentation — Jenkins / Keycloak

## Keycloak (existing)
- Realm `lakehouse`; issuer `http://keycloak.localhost:8080/realms/lakehouse`.
- Container-reachable base: `http://keycloak:8080`.
- Discovery advertises `keycloak.localhost` for every endpoint.
- Group claim pattern: `oidc-group-membership-mapper`, `claim.name=groups`, `full.path=false`.

## Jenkins OIDC (to verify during design)
- The maintained option is the Jenkins **OpenId Connect Authentication** plugin (`oic-auth`). It supports well-known discovery or manual endpoints (authorization, token, JWKS, end-session), a groups claim, and a built-in "escape hatch" local admin credential. It can be configured through `configuration-as-code`.
- Callback URL pattern: `<jenkins root URL>/securityRealm/finishLogin`.
- Logout: `<jenkins root URL>/logout`, with optional end-session redirect.
- Exact plugin version, configuration-as-code keys, and PKCE support must be verified against the pinned Jenkins LTS during design.

## Authorization (to verify)
- `matrix-auth` (installed in the legacy home) supports group-based permissions. Group names from the OIDC `groups` claim become Jenkins authorities.
