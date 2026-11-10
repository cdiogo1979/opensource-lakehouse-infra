# Domain Entities — Airflow Keycloak SSO

## Entities

### User
- Identifier: Keycloak subject or canonical user ID
- Attributes: username, email, group memberships, authentication state
- Responsibilities: identity resolution for browser login and role evaluation

### Realm
- Name: `lakehouse`
- Responsibilities: owns the Airflow client, issuer metadata, and application-specific groups

### Client
- Name: `airflow`
- Type: confidential browser OIDC client
- Responsibilities: receives the login callback and participates in the token exchange process

### Group
- Name: approved Keycloak group names used for Airflow role mapping
- Responsibilities: defines the authorization decision set for the Airflow web UI

### Airflow Role
- Values: `Admin`, `User`, `Viewer`
- Responsibilities: final application authorization for UI access and standard Airflow permissions

### Callback Endpoint
- URLs: `http://localhost:8085/auth/oauth-authorized/keycloak` and `http://127.0.0.1:8085/auth/oauth-authorized/keycloak`
- Responsibilities: completes the browser login and provides the code/token exchange target

### Local Break-Glass Login
- Identity: the existing Airflow FAB administrator identified by `AIRFLOW_ADMIN_USERNAME`
- Credential: the existing protected Airflow administrator password
- Responsibilities: provide a local password-authenticated recovery path alongside Keycloak OIDC; reject other local usernames

### Airflow Login Surface
- Methods: Keycloak OIDC and local administrator password authentication
- Responsibilities: present the standard Keycloak route and the separate local break-glass route without changing API or service-account authentication

## Relationships
- A `User` belongs to one or more `Group` records in the `lakehouse` realm.
- A `Group` maps to exactly one approved `Airflow Role` in the controlled mapping matrix.
- A `Client` is associated with the `Realm` and authenticates the user for the Airflow web UI.
- `Airflow Role` drives final UI authorization after token validation.
- The `Local Break-Glass Login` authenticates only the configured local administrator independently of Keycloak claims.
- The `Airflow Login Surface` presents both login methods while keeping their identities and credential checks separate.
