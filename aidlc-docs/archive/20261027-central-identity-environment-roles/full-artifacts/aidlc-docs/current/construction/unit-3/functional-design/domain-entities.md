# Unit 3 Functional Design — Domain Entities

## Identity and policy entities

| Entity | Meaning | Key attributes / constraints |
|---|---|---|
| `Principal` | Authenticated human or workload identity presented to a service | Canonical user/service name; Kerberos principal; no implicit aliasing. Human Spark principal must match that user's RustFS identity. |
| `RoleGroup` | FreeIPA group that assigns one data role | `lakehouse-developers`, `lakehouse-analysts`, `lakehouse-writers`; membership source is FreeIPA after cutover. Missing/conflicting membership means deny. |
| `AuthorizationDecision` | Result for one principal, resource, and operation | Principal, object, environment, operation, policy layer (`HMS`/`RustFS`), outcome, bounded reason. Must not contain secret material. |
| `CredentialContext` | Credentials available to a running Spark client or service | Independent Kerberos ticket cache and S3 credential provider. Must identify one effective principal; human context cannot contain writer credentials. |

## Catalog entities

| Entity | Meaning | Key attributes / constraints |
|---|---|---|
| `Environment` | Data lifecycle boundary | `production`, `development`, or `uat`; maps exactly to one approved bucket. |
| `StorageBucket` | RustFS object boundary | `lake` (production), `lake-dev` (development), `lake-uat` (UAT). Existing production objects are preserved. |
| `Database` | HMS namespace and root data location | Name, environment, explicit warehouse URI, owner/creator metadata. `lhdev*` maps to development; UAT names follow approved UAT classification. Existing conflicting locations are not auto-corrected. |
| `Table` | Iceberg/Hive table registered in HMS | Database identity, metadata location, data location, format, owner. Must remain within the database's approved bucket; external paths denied by default. |
| `Partition` | Table subdivision where represented in metadata | Parent table and object location; must not escape its environment bucket. |
| `WarehouseRoot` | Environment-specific base URI for newly created databases | Production `s3a://lake/warehouse/`; development `s3a://lake-dev/warehouse/`; UAT `s3a://lake-uat/warehouse/`. These are target rules; current config points only at `lake`. |

## Service entities

| Entity | Meaning | Constraints |
|---|---|---|
| `HiveMetastoreService` | Kerberized Thrift metadata endpoint | Current URI `thrift://hive-metastore:9083`; service principal and configured storage credentials are not the caller's RustFS identity. |
| `SparkClient` | Direct Spark process using Iceberg HiveCatalog and object storage | Current catalog is `iceberg` backed by `HiveCatalog`; effective HMS and S3 caller identities must be verified independently. |
| `RustFSObjectRequest` | S3 API call for list/read/write/delete/multipart | Authorized from the S3 credential's RustFS IAM policy; S3A POSIX permission stubs are not an authorization policy. |
| `RangerPolicyContext` | StarRocks query authorization path | Out of direct Spark flow; cannot authorize direct HMS or RustFS requests. |

## Relationships

```text
Principal ──member of──> RoleGroup ──selects──> AuthorizationPolicy
SparkClient ──Kerberos request──> HiveMetastoreService ──resolves──> Database ──contains──> Table ──contains──> Partition
SparkClient ──S3 credential──> RustFSObjectRequest ──targets──> StorageBucket
Environment ──maps to──> WarehouseRoot ──resolves to──> StorageBucket
```

HMS metadata decisions and RustFS object decisions are distinct. A future supported metadata authorizer must consume the intended principal and environment mapping; until verified, `AuthorizationDecision` at the HMS layer is a required behavior with an unresolved implementation capability.

## State and invariants

- Exactly one environment and bucket are resolved for each new database.
- Every table and partition remains in its parent database's environment boundary.
- Existing production database and object locations are preserved until separately reviewed.
- A human Spark session never inherits the ETL writer's broad S3 identity.
- A Kerberos service identity does not imply a RustFS identity, or vice versa.
- Unknown or conflicting identity/location state denies access and does not mutate metadata or objects.
- Storage-based HMS authorization over S3A/RustFS remains unproven until the acceptance gate passes.
