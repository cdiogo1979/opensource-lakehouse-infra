# Unit 2 Identity and Permission Provisioning — Domain Entities

## Core Entities

### Principal

Represents a Kerberos identity in the disposable PoC realm.

| Attribute | Description |
|---|---|
| `principal_name` | Fully qualified realm principal, for example `write-service-account@LAKEHOUSE.LOCAL`. |
| `identity_type` | `admin`, `writer`, `test_user`, or `service`. |
| `keytab_reference` | Path/reference to a local protected keytab; never the keytab contents. |
| `lifecycle_state` | `missing`, `created`, `present`, `rotation_required`, or `failed`. |
| `owner_component` | Kerberos KDC. |

The Hive Metastore service principal is an existing service entity and is preserved by Unit 2.

### Component Account

Represents a component-owned account, role, or access key associated with a logical identity.

| Attribute | Description |
|---|---|
| `logical_identity` | `admin`, `write-service-account`, `user_a`, or `user_b`. |
| `component` | KDC, Dremio, RustFS, PostgreSQL, Hive/Hadoop, Spark, or JupyterHub. |
| `native_name` | Component-specific login, role, access-key identifier, or mapped username. |
| `credential_reference` | Local runtime file/path reference; no credential value is included in design output. |
| `permission_profile` | Component-owned roles/policies requested for the identity. |
| `lifecycle_state` | `missing`, `created`, `present`, `deferred`, or `failed`. |

One logical identity may map to multiple component accounts, but each component account retains its own credential and authorization boundary.

### Credential Artifact

Represents protected local authentication material without storing its secret value in application metadata.

| Attribute | Description |
|---|---|
| `artifact_type` | Keytab, Dremio password, RustFS access key/secret, PostgreSQL role password, or other component-native credential. |
| `identity_reference` | Owning logical identity and component account. |
| `local_reference` | Protected, ignored runtime path. |
| `consumer_components` | Exact component(s) permitted to read/use the artifact. |
| `rotation_state` | `stable`, `rotation_requested`, or `consumer_update_pending`. |

Secrets are not printed, copied across account boundaries, or embedded in images or tracked configuration.

### Permission Grant

Represents an authorization decision configured by the owning component.

| Attribute | Description |
|---|---|
| `subject` | Component identity receiving the permission. |
| `resource` | Hive database/table, RustFS bucket prefix, Dremio Space, or PostgreSQL resource. |
| `action` | Component-supported operation such as create, read, write, or administer. |
| `grant_owner` | Hive/Hadoop, RustFS, Dremio, or PostgreSQL. |
| `phase` | `initial_setup`, `post_etl`, or `component_integration`. |
| `verification_state` | `unverified`, `configured`, `allowed`, `denied_as_expected`, or `blocked`. |

The provisioner coordinates grant setup but does not evaluate requests at runtime.

### Provisioning Run

Represents one idempotent execution of identity setup.

| Attribute | Description |
|---|---|
| `run_id` | Non-secret identifier for the run. |
| `phase` | `initial_identities` or `post_etl_reader_grants`. |
| `started_at` | Local run start time. |
| `component_results` | Per-component `created`, `already-present`, `deferred`, or `failed` results. |
| `overall_state` | `running`, `complete`, or `failed`. |
| `diagnostic` | Redacted component/operation error, with no credential material. |

## Relationships

```text
Logical Identity 1 ─── * Principal
Logical Identity 1 ─── * Component Account
Component Account 1 ─── * Credential Artifact
Component Account 1 ─── * Permission Grant
Provisioning Run 1 ─── * Component Account result
Permission Grant * ─── 1 Owning Component
```

## Domain Boundaries

- Kerberos authenticates principals and issues tickets; it does not decide Hive, RustFS, Dremio, or PostgreSQL authorization.
- Component Accounts belong to their native component. The coordinator does not merge their credential stores.
- Permission Grants are records of requested component-owned setup. Runtime allow/deny decisions remain in Hive/Hadoop, RustFS, Dremio, and PostgreSQL.
- A `deferred` grant is not equivalent to a configured or verified grant. For example, database reader grants wait for Unit 3 to create the databases.
- A successful Provisioning Run proves setup operations completed, not that effective-user propagation or cross-engine authorization works.
