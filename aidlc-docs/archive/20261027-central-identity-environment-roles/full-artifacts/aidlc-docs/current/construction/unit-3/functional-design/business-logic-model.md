# Unit 3 Functional Design — Business Logic Model

## Purpose

Define the intended metadata and data authorization path for direct Spark clients using the Hive Metastore (HMS) and RustFS. This document records both the approved target behavior and the enforcement boundary found in the pinned design. It does not authorize implementation or runtime changes.

## Actors and trust boundaries

1. **Human Spark client** obtains a Kerberos identity for its signed-in user and RustFS S3 credentials for that same user. JupyterHub credential delivery is designed in Unit 4; this document defines the identity contract only.
2. **ETL Spark client** uses the non-interactive `write-service-account` Kerberos principal and its RustFS writer credentials. It must not be used as a human-session fallback.
3. **Hive Metastore** authenticates Thrift clients with Kerberos SASL and makes metadata decisions. It has its own service principal and currently has configured RustFS credentials.
4. **RustFS** authorizes each S3 request using the credentials presented by that request. Its bucket IAM policies are the data-plane authority for direct Spark access.
5. **FreeIPA** is the intended source of users and role-group memberships after the separately approved authority cutover. The active MIT KDC remains authoritative until Unit 6; this unit does not perform that cutover.

## Request flow

```text
Spark SQL / Iceberg operation
  ├─ HMS Thrift request ── Kerberos principal ──> HMS metadata checks
  └─ S3A / Iceberg S3FileIO request ── RustFS S3 credentials ──> bucket IAM policy
```

Kerberos identity and S3 identity are independent credentials. A successful HMS request does not grant S3 access, and metadata visibility across environments is accepted. Direct Spark data access must use the caller's own RustFS credentials. Ranger governs supported StarRocks query paths only and is not in this direct Spark request flow.

## Intended policy decision sequence

For every operation:

1. Resolve the authenticated principal to exactly one approved role (or the separate administrator mapping). Missing, ambiguous, conflicting, or stale role identity is denied.
2. Resolve database/table/partition location from explicit metadata. Apply the environment mapping: production → `lake`; development including `lhdev*` → `lake-dev`; UAT → `lake-uat`.
3. Reject defaulted, external, cross-bucket, or otherwise unapproved locations. Do not silently fall back to the production warehouse.
4. HMS returns the requested metadata. RustFS independently applies the caller's S3 permissions to each object request and decides whether Spark can read or mutate data.
5. The operation succeeds only when every enforcement layer required for the action allows it. A metadata allow is not a data allow; a data allow is not a metadata allow.
6. On unavailable identity, HMS, or RustFS services, malformed location, ambiguous database classification, or credential failure, fail closed and expose no broader fallback identity.

## Authorization boundary and limitation

The repository configures `AuthorizationPreEventListener`, `StorageBasedAuthorizationProvider`, read authorization, Kerberos SASL, and `hive.metastore.execute.setugi=true`. Those settings describe the intended HMS path but do not prove the target matrix.

Apache Hive describes storage-based authorization as checking filesystem permissions for database/table/partition directories. Apache Hadoop documents that S3A reports stub metadata (directory mode 777, file mode 666) and does not enforce authorization checks against those stub permissions; actual access is controlled by S3 credentials/policies. Therefore the current design cannot claim that `StorageBasedAuthorizationProvider` enforces per-user metadata visibility/operations on RustFS-backed S3A paths. `hive.metastore.execute.setugi` is documented for unsecure mode and as best effort; it is not a substitute for authenticated per-user S3 credentials or a supported metadata authorizer.

The current rendered HMS configuration also contains the service's S3 credentials, while the long-lived Spark service startup obtains the writer identity. The notebook image has a separate per-session identity entrypoint, but end-to-end alignment between the HMS caller, S3 credentials, and HMS authorization decision has not been verified. No user authorization guarantee is inferred from these files alone.

The user accepts cross-environment database/table metadata visibility. Unit 3 Build and Test must prove the RustFS object allow/deny matrix through real Spark/Iceberg reads and writes with disposable data and each role's own credentials. This design does not guarantee analyst Hive metadata DDL is denied. If that becomes a requirement, stop before implementation/cutover and request an architecture decision for a supported HMS authorizer. Do not represent RustFS bucket policies as a control over metadata changes.

## Intended operation outcomes

| Operation | Metadata layer | RustFS layer | Overall result |
|---|---|---|---|
| Discover database/table/partition | May be visible across environments | No data read necessarily occurs | Metadata visibility is accepted; it does not grant data access |
| Read table data | Must allow metadata resolution | Caller credential must have object read/list as required | Allow only if both allow |
| Create/write/overwrite | Must allow the metadata mutation | Caller credential must have required write/list/delete/multipart rights | Allow only if both allow |
| Drop/delete | Must allow metadata mutation | Caller credential must have object deletion rights; metadata removal alone is insufficient | Allow only if both allow |
| Unknown or conflicting location | Deny | Do not issue a request using a broader identity | Deny |

The exact actions required for S3A/Iceberg operations depend on the pinned connector and RustFS behavior and are acceptance-test items; the operation-level role matrix is in `business-rules.md`.

## Database location lifecycle

- Existing production databases remain in their existing `lake` locations; no rewrite or migration is implied.
- New production databases must explicitly use `s3a://lake/warehouse/<database>/`.
- New development databases, including names beginning `lhdev`, must explicitly use `s3a://lake-dev/warehouse/<database>/`.
- New UAT databases must explicitly use `s3a://lake-uat/warehouse/<database>/`.
- An existing database with an absent, conflicting, or cross-environment location is quarantined from automated alteration: report the conflict and stop. Never relocate existing objects during normal database initialization.
- Table and partition locations must remain beneath the owning database's approved bucket/environment. External locations require a separately approved rule and are denied by default.

## Operational outcomes

Authorization is evaluated per request, not by UI visibility. Errors should identify the denied principal, object, operation, and authorization layer without printing keys, secrets, keytabs, or tickets. HMS/RustFS outages, expired tickets, missing S3 credentials, or policy lookup failures return a bounded failure and do not retry as `write-service-account`.

## Traceability

| Requirement | Functional rule |
|---|---|
| US-03: preserve production | R1, R5; existing locations are read-only inputs to design and must not be migrated |
| US-04: isolate dev/UAT | R2–R4; explicit database roots and no fallback |
| US-05: developer scope | Approved role authorization matrix; R8–R12 |
| US-06: analyst scope | Approved role authorization matrix; R8–R12 |
| US-07: writer scope | Approved role authorization matrix; R8–R12 |
| US-09: per-user Spark identity | Credential-context rules R11–R12; no service fallback |

### Primary technical references

- Apache Hive, [Storage Based Authorization in the Metastore Server](https://hive.apache.org/docs/latest/user/storage-based-authorization-in-the-metastore-server/)
- Apache Hive, [Configuration Properties: `hive.metastore.execute.setugi`](https://hive.apache.org/docs/latest/user/configuration-properties/)
- Apache Hadoop, [Hadoop-AWS: S3A object authorization model](https://hadoop.apache.org/docs/r3.4.3/hadoop-aws/tools/hadoop-aws/index.html)
- Apache Hadoop, [S3A authentication and credentials](https://hadoop.apache.org/docs/current/hadoop-aws/tools/hadoop-aws/authentication.html)
