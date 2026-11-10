# Unit 1 Domain Entities — JupyterHub Foundation and OIDC Admission

## Entity model

```mermaid
erDiagram
  IDENTITY_PROVIDER ||--o{ AUTHENTICATED_IDENTITY : issues
  AUTHENTICATED_IDENTITY ||--|| HUB_AUTH_STATE : owns
  AUTHENTICATED_IDENTITY ||--o{ ROLE_MEMBERSHIP : has
  AUTHENTICATED_IDENTITY ||--o| USER_SERVER : controls
  AUTHENTICATED_IDENTITY ||--|| USER_HOME : owns
  USER_SERVER }o--|| USER_HOME : mounts

  IDENTITY_PROVIDER {
    string issuer
    string realm
  }
  AUTHENTICATED_IDENTITY {
    string issuer_subject
    string login_name
    string display_name
    string admission_status
  }
  ROLE_MEMBERSHIP {
    string group_name
    string membership_status
  }
  HUB_AUTH_STATE {
    string identity_key
    string protected_token_state
    datetime authenticated_at
    datetime expires_at
  }
  USER_SERVER {
    string server_id
    string lifecycle_state
    datetime started_at
  }
  USER_HOME {
    string owner_identity_key
    string persistence_state
  }
```

## Entity definitions

### Identity Provider

Represents the configured Keycloak realm trusted by Hub for interactive sign-in. Its issuer identifies the authority that issued an authentication result. Unit 1 does not provision or administer the realm.

### Authenticated Identity

Represents one Hub user authenticated by an identity provider. The stable identity key is the issuer plus subject; the login name and display name are attributes and must not be treated as substitutes for the stable key. Admission status is derived from current approved group memberships.

### Role Membership

Represents a user's current membership in a Keycloak role group. For Hub admission, the accepted group values are `role-default-developer` and `role-default-analyst`. Both may coexist and are preserved; downstream Polaris authorization applies the union of grants. Other role groups do not confer Hub admission.

### Hub Auth State

Represents Hub-owned OIDC session data linked to one authenticated identity, including protected OAuth token material and timestamps needed to assess the Hub session. It is encrypted at rest and unavailable to another user or user server. Unit 2 defines access-token refresh and token-broker exchange details.

### User Server

Represents the one default Jupyter/Spark server associated with an authenticated identity. Lifecycle states are starting, running, stopping, stopped, failed, or denied. The server may start only while its owner is currently eligible.

### User Home

Represents the persistent notebook/file storage owned by one stable Hub identity. It is mounted only by that identity's server. Server stop/restart does not delete it; token state and confidential credentials are not stored there.

## Relationships and invariants

- An authenticated identity is tied to one trusted issuer/subject pair; login/display names are not the stable storage owner key.
- An identity may have zero or more role memberships, but spawn eligibility requires at least one of the two approved groups.
- One identity owns at most one default server and exactly one logical persistent home for this initial journey.
- A server can access only its owner's home and can run only while the owner's admission is valid.
- Hub auth state is associated with one identity and remains Hub-side; a user home is a separate persistence boundary.
- Deleting or stopping a server does not imply deleting the identity's home or the Hub's lifecycle/audit record.
