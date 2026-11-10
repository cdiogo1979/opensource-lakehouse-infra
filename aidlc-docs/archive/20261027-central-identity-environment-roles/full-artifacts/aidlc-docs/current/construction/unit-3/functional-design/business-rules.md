# Unit 3 Functional Design — Business Rules

## Environment and location rules

| ID | Rule |
|---|---|
| R1 | Existing production databases and objects in `lake` are preserved in place; this unit performs no migration or deletion. |
| R2 | New production database location is explicit: `s3a://lake/warehouse/<database>/`. |
| R3 | Development databases, including `lhdev*`, use `s3a://lake-dev/warehouse/<database>/`. |
| R4 | UAT databases use `s3a://lake-uat/warehouse/<database>/`. |
| R5 | Missing/ambiguous environment classification, implicit warehouse defaults, cross-bucket locations, or conflicting existing locations fail closed. No automatic fallback to `lake` and no automatic relocation. |
| R5a | Tables and partitions remain under the owning database's environment bucket. External locations are denied unless separately approved. |

## Role authorization matrix

This is the approved target policy. The user accepts that database/table metadata may be visible across environments. RustFS enforces object reads and writes for direct Spark sessions. Metadata visibility is not an authorization boundary in this design. HMS metadata mutation restrictions remain unproven and must not be represented as enforced; analyst DDL must be avoided until an HMS authorizer is separately approved and verified.

| Principal | HMS metadata: prod (`lake`) | HMS metadata: dev (`lake-dev`) | HMS metadata: UAT (`lake-uat`) | RustFS read | RustFS write/overwrite/delete |
|---|---:|---:|---:|---|---|
| `developer-user` / `lakehouse-developers` | Visible; no access guarantee | Visible; no access guarantee | Visible; no access guarantee | All three buckets | `lake-dev` only |
| `analyst-user` / `lakehouse-analysts` | Visible; no access guarantee | Visible; no access guarantee | Visible; no access guarantee | `lake` only | Deny all buckets |
| `write-service-account` / `lakehouse-writers` | Visible; no access guarantee | Visible; no access guarantee | Visible; no access guarantee | All three buckets | All three buckets |
| `admin` | Existing metadata visibility | Existing metadata visibility | Existing metadata visibility | Preserve existing admin mapping | Preserve existing admin mapping |
| Unknown, missing, or conflicting role | Metadata may be visible | Metadata may be visible | Metadata may be visible | Deny | Deny |

## Operation rules

| ID | Operation | Required decision |
|---|---|---|
| R6 | Database discovery/list/description | Metadata names may be visible across environments; this is not an authorization boundary. |
| R7 | Table/partition list and metadata read | Metadata may be visible across environments. Users must not infer data access from metadata visibility. |
| R8 | Table data read | The caller's own RustFS identity must authorize the actual object reads required by Spark/Iceberg. A denied RustFS read must fail the query; no writer/admin fallback is allowed. |
| R9 | Create database/table/partition, append, overwrite, or alter data | RustFS must deny unauthorized object writes, including connector-required list, multipart, and delete operations. Developer writes only dev; analyst writes nowhere; writer may write all. HMS metadata DDL authorization is not guaranteed by this design; analysts must not issue DDL. |
| R10 | Drop database/table/partition or delete data | RustFS denies object deletion outside the role scope. HMS metadata drop authorization is not guaranteed; analysts must not issue DDL and metadata-only changes are not proof of data deletion. |
| R11 | Kerberos authentication | Human client must present its own valid principal. `write-service-account` is ETL-only and cannot be substituted for an absent/expired human ticket. |
| R12 | RustFS authentication | Each direct Spark process must use the RustFS credentials for the same effective user/role. Never load the broad writer key into a human session. |
| R13 | Admin | Preserve the existing platform `admin` mapping; this unit does not widen or redefine it. |
| R14 | Ranger | Apply Ranger only to the supported StarRocks query integration. Do not count Ranger as authorization for direct Spark-to-HMS or Spark-to-RustFS requests. |

## Error and recovery rules

| ID | Condition | Required behavior |
|---|---|---|
| R15 | Unknown principal, no role, multiple/conflicting roles, or failed directory lookup | Deny; do not infer a default role. |
| R16 | Expired/missing Kerberos ticket or HMS SASL failure | Fail the request; do not retry as a service principal. |
| R17 | Missing, invalid, or denied RustFS credentials | Fail the object operation; do not retry with writer/admin credentials. |
| R18 | HMS, KDC/FreeIPA, or RustFS unavailable | Fail closed; no authorization cache or alternate credential may broaden access. Cache semantics must be characterized in Build and Test. |
| R19 | Database metadata conflicts with the environment mapping | Stop before mutation and report the expected/observed location without exposing credentials. |
| R20 | Authorization rejection | Report which layer denied (HMS metadata, Kerberos authentication, or RustFS object access) without logging secrets, keytabs, or ticket contents. |

## Acceptance probes for Unit 3 Build and Test

Use disposable databases, tables, and objects only. Probe the same operation separately through HMS metadata and RustFS object APIs so a denial is attributed to its layer.

1. Confirm metadata discovery can include out-of-environment names and does not grant object access.
2. Read populated disposable tables with Spark: analyst succeeds in prod and receives a RustFS authorization denial in dev/UAT; developer reads all; writer reads all.
3. Attempt object writes/overwrites/deletes through Spark in each bucket; assert developer can mutate only dev, analyst cannot mutate any bucket, and writer can mutate all. Attribute results to RustFS.
4. Do not use analyst database/table/partition DDL as an authorization test; HMS metadata mutation is not guaranteed by this design.
5. Try implicit, cross-bucket, external, and conflicting locations; verify failure before any object mutation.
6. Expire/remove the caller ticket and separately remove/deny its S3 credentials; verify there is no writer-identity fallback.
7. Verify `admin` retains the existing documented behavior, separately from role-based human and ETL identities.
8. Test HMS/RustFS outage and recovery plus authorization cache behavior; outage must not produce broader access.

### Architecture acceptance gate

The current Hive storage provider depends on filesystem permission metadata. Apache Hadoop documents S3A permission values as stubs that are not enforced by S3A. The user accepts cross-environment metadata visibility, so metadata confidentiality is no longer a Unit 3 acceptance criterion. Unit 3 instead requires proof that direct Spark/Iceberg reads and writes use the caller's own RustFS identity and are denied outside its bucket policy. This does not protect Hive metadata mutations; an HMS authorizer remains a separate future decision if analyst DDL must be blocked.
