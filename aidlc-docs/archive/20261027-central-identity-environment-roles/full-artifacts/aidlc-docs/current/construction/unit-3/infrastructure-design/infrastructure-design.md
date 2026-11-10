# Infrastructure Design — Hive Metastore and Direct Spark Authorization

## 1. Scope and decisions

This design prepares the existing Hive Metastore, Spark, and RustFS setup for controlled Unit 3 authorization verification. It does not add a service, plugin, HiveServer2, gateway, proxy, published port, or version change. It does not change identity authority, role memberships, RustFS policies, existing database locations, or data.

The answers to the Unit 3 Infrastructure Design Plan are A/A/A/A/A/A/A/A, using the recommended options. Scope is limited to existing Hive/Spark configuration templates, database initialization/validation logic, and related startup settings if later implementation is separately authorized.

**Authorization boundary:** cross-environment database/table metadata visibility is accepted. The actual pinned stack must demonstrate the direct Spark/Iceberg object read/write matrix using the matching user's RustFS identity with disposable test data. This design does not guarantee analyst HMS metadata DDL restrictions; those require a separately approved authorization design if needed.

## 2. Existing service boundary

Retain the current components and internal endpoints:

| Component | Existing role | Unit 3 boundary |
|---|---|---|
| Hive Metastore 3.1.3 | Kerberos-SASL Thrift metadata service at `thrift://hive-metastore:9083` | Retain current service; inspect effective principal and metadata authorization behavior. |
| Spark 3.5.5 / Iceberg 1.8.1 | Direct Spark client using the HiveCatalog and RustFS object client | Retain current image/version and direct HMS/S3 request pattern. |
| RustFS 1.0.0 | S3-compatible storage and IAM enforcement for object requests | Retain current image and policy state; use the caller identity for object probes. |
| MIT KDC | Current runtime Kerberos authority | Remains authoritative through Unit 3; no alias, realm, principal, or keytab cutover. |
| FreeIPA | Isolated validation identity service | Remains isolated. Unit 3 design does not attach general workloads or change production authority. |

No host ports or service networks are added. Existing Compose service endpoints remain internal.

## 3. Identity and credential boundaries

Kerberos and RustFS authentication remain separate:

- Spark's HMS connection presents a Kerberos principal using the existing SASL transport.
- Spark's S3A/S3FileIO requests present RustFS S3 credentials associated with the effective caller.
- An allow at one service does not imply an allow at the other.
- Human test contexts must use only their own credential material. The writer S3 key and writer keytab remain restricted to ETL/service use and are never a human fallback.
- Keep credentials in protected read-only files and private per-process caches with restrictive ownership/modes. Do not place secret values in config templates, ordinary environment literals, command arguments, or diagnostics.

The active KDC stays MIT until Unit 6. The isolated FreeIPA instance is not joined to the general workload network. This design does not provision or switch production users to FreeIPA. Because the approved role identities may not yet exist in the active authority, the subsequent Build and Test plan must identify isolated test principals and RustFS credentials before any role probe; it must not silently create or route users in production.

The current HMS configuration includes service-side RustFS credentials. These establish only the metastore process's S3 identity, not the Spark caller's S3 identity. The current long-lived Spark service uses the ETL writer context; notebook sessions have their own identity entrypoint, but their end-to-end HMS/S3 relationship remains unverified. Neither setup is considered proof of per-user authorization.

## 4. Metadata and object authorization boundary

HMS metadata operations use Kerberos SASL and the configured Hive authorization listener/provider. RustFS object operations use each caller's S3 credential and IAM policy. Tests must identify the principal at each boundary and distinguish:

1. Kerberos authentication failure;
2. RustFS object read/write allow/deny through actual Spark/Iceberg operations;
3. RustFS object allow/deny.

The configured `StorageBasedAuthorizationProvider` remains unchanged. Hive documents storage-based checks against filesystem permissions; Hadoop documents S3A permission metadata as stubs that S3A does not enforce. Cross-environment metadata visibility is accepted; the runtime gate concerns object reads and writes.

**Hard stop:** do not claim or deploy role-based metadata protection unless disposable tests demonstrate the approved matrix on the pinned stack. If metadata outside the user's scope remains discoverable or mutable, return for architecture approval. RustFS bucket policies, Ranger for StarRocks, and user-interface hiding are not substitutes.

## 5. Database location infrastructure

The new database mapping is explicit:

| Environment | Bucket | New database warehouse root |
|---|---|---|
| Production | `lake` | `s3a://lake/warehouse/<database>/` |
| Development, including `lhdev*` | `lake-dev` | `s3a://lake-dev/warehouse/<database>/` |
| UAT | `lake-uat` | `s3a://lake-uat/warehouse/<database>/` |

Infrastructure may provide explicit locations for new databases and read-only validation for existing metadata. Existing production database/table/partition paths remain unchanged. Before any later authorized mutation, reject an implicit default, ambiguous environment, external path, cross-bucket path, table/partition path outside its database root, or conflicting existing location. Do not auto-relocate, rewrite, delete, or migrate data.

Changing a global catalog warehouse default alone is insufficient evidence that each database uses the correct environment. Verification reads back the actual HMS database and table locations and checks the corresponding RustFS object path.

## 6. Request limits, retries, and failure handling

Every HMS, identity, and RustFS request must have a finite connect/read/request timeout. Retries are bounded and restricted to safe transient failures. Do not retry authentication, authorization, conflict, invalid-location, or malformed-response failures. Do not blindly retry mutations; read state before a safe retry. Exact timeout values are established during implementation verification because no end-to-end latency SLA was selected.

On missing/expired credentials, conflicting role, ambiguous location, service outage, unknown response, or indeterminate authorization result, fail closed. There is no writer/admin fallback. A partial multi-step write or metadata operation is reported incomplete and requires review; do not claim cross-service atomicity or automatically revert unknown state.

## 7. Runtime permissions and diagnostics

Use existing local runtime/log locations only. Keep Kerberos caches, keytabs, S3 credential files, and temporary credential material private to the owning test or service identity. No new audit service or retention store is added.

Diagnostics may include timestamp, bounded duration, sanitized principal/role, environment/resource classification, operation category, enforcement layer, outcome, and an allowlisted failure category. Exclude passwords, S3 keys, keytabs, ticket contents, raw request/response bodies, and object contents. Avoid logging object identifiers unless required to prove a disposable probe; test identifiers must be synthetic.

## 8. Disposable verification boundary

Later Build and Test requires an approved plan and must identify its principals, HMS metadata, and RustFS credentials in advance. Use disposable databases/tables and unique test object keys with pre/post inventory. Any negative role probe must use credentials and locations that cannot mutate production objects. Stop if test isolation cannot be proven.

Required probes include database discovery, table/partition metadata, reads, create/append/overwrite, drop/delete, explicit and unsafe locations, identity mismatch, dependency outage, cache/revocation delay, and log redaction. A result is successful only when expected HMS and RustFS decisions are independently read back and unrelated production inventory remains unchanged.

## 9. Preservation and change control

- Preserve the `lake` bucket, all existing production objects, database/table locations, writer S3 key, admin privilege mapping, and user workspaces.
- Unit 3 does not provision or revoke production identities, modify role memberships/policies, rotate credentials, or perform the MIT-to-FreeIPA cutover.
- Any new service, authorizer, plugin, gateway, HiveServer2, network exposure, or version change requires architecture review.
- If the HMS metadata gate fails, pause before changing infrastructure for an alternate enforcement path.

## 10. Traceability and deferred decisions

| Approved requirement | Infrastructure decision |
|---|---|
| `HMS-NFR-01`–`02` | Retain fixed PoC components and use bounded requests; no latency SLA. |
| `HMS-NFR-03`–`06` | Preserve identity boundary, fail closed, prohibit fallback, and measure revocation. |
| `HMS-NFR-07`–`10` | Per-identity protected files/caches, internal networks, and sanitized existing logs. |
| `HMS-NFR-11`–`12` | Explicit location validation, read-only baseline inventory, and fail-closed conflicts. |
| `HMS-NFR-13`–`14` | Preserve versions/services and use disposable evidence. |

The following remain Build and Test gates, not assumed design facts: effective principal seen by HMS; actual database/table/partition locations; S3A versus S3FileIO credential selection; Spark use of role-specific RustFS credentials; object read/write denial; role-cache and ticket revocation delay; safe timeout/retry values; and redaction of real failure output. If analyst metadata DDL restrictions are required, return to architecture review.
