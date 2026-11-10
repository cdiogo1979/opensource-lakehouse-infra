# Unit 1 Functional Design — Domain Entities

This model describes logical information exchanged by foundation components. It does not prescribe a database schema or concrete configuration format.

## Entity Model

| Entity | Meaning | Key attributes | Relationships |
|---|---|---|---|
| Deployment State | Lifecycle state of the local Compose PoC. | state (`absent`, `initializing`, `ready`, `failed`, `stopped`, `reset`); last completed step; failure component/reason. | Contains catalog, KDC, bucket, and service readiness states. |
| Initialization Step | One repeatable setup operation. | step identifier; owning component; input references; outcome (`created`, `already-present`, `ready`, `failed`); safe-to-retry indicator. | Ordered by lifecycle dependencies; failure blocks dependent steps. |
| Kerberos Principal | Identity in the disposable local realm. | principal name; principal category; realm; keytab reference (not keytab contents); lifecycle state. | Authenticates a service or user; has separate component-native credentials where needed. |
| Component Credential | Authentication material owned by a component. | component; principal/account reference; credential kind; local secret reference; scope; rotation/reset state. | A principal may map to multiple distinct component credentials; credential values are never modeled in docs/logs. |
| Hive Database | Catalog namespace for sample data. | name (`databaseA` or `databaseB`); owner (`write-service-account`); storage location; initialization state. | Contains Hive tables; maps to a RustFS warehouse path; has reader access bindings. |
| Hive Table | Iceberg table registered in the catalog. | database; name; owner; table location; schema reference; initialization state. | Belongs to one database and maps to RustFS objects. |
| Storage Resource | RustFS bucket or warehouse path associated with metadata. | bucket; path/prefix; resource type; initialization state. | Contains objects; is associated with a Hive database/table and a storage permission binding. |
| Authorization Binding | Component-owned permission relationship for an identity and resource. | subject identity; owning component; resource; actions; effective period/state; grant source. | Hive Metastore or RustFS applies its own semantics; the provisioner may request setup but does not own runtime evaluation. |
| Authorization Outcome | Result of an access attempt. | effective user; engine/client; database/table; action; allow/deny; reason category; timestamp. | References an authorization binding or a failed/unavailable policy evaluation; contains no secret values. |

## Relationships

- One deployment has one disposable Kerberos realm, one Hive metadata store, and one or more RustFS buckets.
- The `lake` bucket contains paths for `databaseA` and `databaseB`; each Hive database contains one or more Iceberg tables, each associated with its own data/metadata paths.
- `write-service-account` owns the sample database/table objects and has scoped create/write bindings for their warehouse paths.
- `user_a` has read bindings for `databaseA` only; `user_b` has read bindings for both databases.
- Dremio local usernames and Jupyter session labels map to the intended Kerberos/effective user according to their component-owned mappings. DummyAuthenticator labels are not verified identities.
- Component credentials remain separate: a Kerberos keytab is not a RustFS secret key or Dremio password.
- Authorization outcomes may be recorded only when the effective identity and the component's authorization decision are observable; otherwise the result is unknown/blocked, not implicitly allowed.

## State Constraints

- A database/table can be `ready` only after Hive metadata and referenced RustFS locations are present.
- An initialization step is idempotent only if repeating it preserves existing data and reports the existing state.
- A failed step does not make dependent resources ready.
- A `reset` deployment state represents an explicit operator action that removes persistent catalog and object-store state; it is never an implicit recovery transition.
