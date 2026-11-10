# Unit 3 Domain Entities — SQL Bootstrap and Catalog Access

## SqlBootstrap

Represents one idempotent reconciliation run against the StarRocks SQL endpoint.

| Attribute | Meaning |
|---|---|
| `run_state` | `PREFLIGHT`, `INSPECTING`, `RECONCILING`, `VERIFYING`, `COMPLETE`, or `FAILED` |
| `failure_category` | Safe category such as `DEPENDENCY_UNAVAILABLE`, `CREDENTIAL_DRIFT`, `STATE_CONFLICT`, or `OPERATION_FAILED`; never raw secret-bearing provider output |
| `started_at` | Run start time |
| `completed_operations` | Names/statuses of completed operations; excludes SQL password values |

**Invariants:** a failed run never reports the target as compliant; no run implicitly rotates credential files or deletes catalog/data objects.

## IcebergExternalCatalog

Represents the StarRocks external catalog over the existing Hive-backed Iceberg lake.

| Attribute | Meaning |
|---|---|
| `catalog_name` | Stable StarRocks catalog identifier |
| `catalog_type` | `iceberg` |
| `iceberg_catalog_type` | `hive` |
| `metastore_endpoint_reference` | Reference to the existing internal Hive Metastore Thrift endpoint |
| `warehouse_reference` | Existing warehouse/bucket path; no data is copied by registration |
| `object_store_endpoint_reference` | Existing internal RustFS S3-compatible endpoint and safe non-secret settings |
| `observed_state` | `ABSENT`, `COMPLIANT`, or `CONFLICTING` |

**Invariants:** registration points to existing HMS metadata and RustFS objects; catalog reconciliation does not drop/recreate databases or tables.

## SqlPrincipal

Represents a native StarRocks SQL login, distinct from Kerberos and RustFS identities.

| Attribute | Meaning |
|---|---|
| `name` | `root`, `admin`, `user_a`, `user_b`, or `write_service_account` |
| `principal_kind` | `BUILT_IN_BOOTSTRAP` or `APPLICATION` |
| `password_reference` | Protected local credential file path/reference only; never the password value |
| `authentication_state` | `ABSENT`, `AUTHENTICATES`, `CREDENTIAL_DRIFT`, or `UNKNOWN` |
| `assigned_roles` | Roles whose effective grants are included in authorization evaluation |

**Invariants:** root and admin have separate password references; stored password files are not silently overwritten; a credential drift state blocks reconciliation.

## SqlRole

Represents an optional StarRocks role used to express the approved database access matrix.

| Attribute | Meaning |
|---|---|
| `name` | Stable role identifier |
| `intended_privileges` | Database/table privileges required by the access matrix |
| `observed_privileges` | Effective direct and inherited privileges discovered during inspection |
| `state` | `ABSENT`, `COMPLIANT`, or `CONFLICTING` |

**Invariants:** role grants cannot expand an identity beyond its access-matrix entry; unrelated roles and grants are preserved.

## ProtectedSqlCredential

Represents a password value held outside the domain model and referenced by a protected file.

| Attribute | Meaning |
|---|---|
| `principal_name` | Associated SQL principal |
| `file_reference` | Path beneath the ignored protected runtime credentials directory |
| `provisioning_state` | `MISSING`, `CREATED`, or `PRESERVED` |

**Invariants:** the secret itself is never represented in logs, tracked configuration, or design state; an existing file is preserved byte-for-byte by routine bootstrap.

## AccessPolicy

Represents the approved database authorization matrix enforced for SQL connections through StarRocks.

| Attribute | Meaning |
|---|---|
| `principal_name` | SQL principal being evaluated |
| `database_name` | `databaseA` or `databaseB` |
| `read_allowed` | Whether SELECT access is allowed |
| `write_scope` | `NONE` or `DML_EXISTING_TABLES` |
| `administrative_scope` | `NONE` or `FULL_STARROCKS` |

**Invariants:** `user_a` is denied databaseB; `user_b` reads both; writer DML is limited to existing tables in both; only `admin` has full StarRocks administration.

## Identity Boundaries

- `SqlPrincipal` authenticates a StarRocks client session.
- The StarRocks service Kerberos identity authenticates StarRocks to HMS.
- The StarRocks RustFS identity authenticates object requests to RustFS.
- These identities have separate credentials and separate authorization domains. StarRocks SQL grants do not grant or revoke direct Spark, HMS, or RustFS access.
