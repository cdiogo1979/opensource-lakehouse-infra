# Unit 5 JupyterHub and Per-User Spark — Domain Entities

## Notebook User

Represents one configured development username accepted by the local Hub.

| Attribute | Description |
|---|---|
| `username` | One of `user_a`, `user_b`, or `admin`. |
| `auth_mode` | `dummy_label`; the person entering the name is not verified. |
| `hub_role` | `admin` for the operator identity; regular user for the two test identities. |
| `kerberos_principal` | Same-named principal in `LAKEHOUSE.LOCAL`; no key material is stored in this entity. |
| `rustfs_identity` | Same-named RustFS account; no key values are stored in this entity. |
| `access_profile` | `user_a`, `user_b`, `admin_operator`, or `not_applicable`. |

## Notebook Session

Represents one user's isolated Jupyter and local Spark runtime.

| Attribute | Description |
|---|---|
| `session_id` | Non-secret identifier for a spawned user server. |
| `username` | The single `Notebook User` mapped to the session. |
| `container_state` | `starting`, `running`, `stopped`, or `failed`. |
| `ticket_state` | `not_requested`, `authenticated`, `expired`, `destroyed`, or `failed`. |
| `ticket_cache_scope` | Private to this container/session; never shared with another user. |
| `workspace_volume` | Persistent volume unique to the username. |
| `credential_references` | Read-only keytab and matching RustFS identity references; never secret values. |
| `spark_state` | `not_started`, `ready`, or `failed`. |

## Spark Authorization Attempt

Represents a direct Spark query used to demonstrate a user's database profile.

| Attribute | Description |
|---|---|
| `attempt_id` | Non-secret identifier for the query attempt. |
| `session_id` | Session in which Spark ran. |
| `effective_principal` | Kerberos principal used by the session. |
| `database_name` | `databaseA` or `databaseB`. |
| `expected_outcome` | `allow` or `deny` from the assigned test-user profile. |
| `actual_outcome` | `allowed`, `denied`, or `error`. |
| `decision_component` | `hive_authorization`, `kerberos`, `hive_connectivity`, `rustfs`, `spark`, or `unknown`. |
| `evidence_state` | `valid`, `failed`, or `blocked`; an error counts as deny only when its authorization decision is established. |
| `diagnostic` | Redacted category/message without credential values. |

## Relationships and Boundaries

- One `Notebook User` may have one active `Notebook Session`; each session has exactly one username and one identity mapping.
- A `Notebook Session` references one user's private ticket cache, keytab, RustFS identity, and persistent workspace.
- A `Spark Authorization Attempt` belongs to one session and is evaluated against that user's access profile.
- Hub authentication labels do not establish a verified human identity.
- Credential references do not place credential material in the session evidence record.
