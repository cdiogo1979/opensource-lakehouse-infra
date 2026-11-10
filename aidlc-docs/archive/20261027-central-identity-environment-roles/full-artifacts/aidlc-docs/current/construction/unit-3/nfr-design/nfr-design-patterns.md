# NFR Design Patterns — Hive Metastore and Direct Spark Authorization

## Design scope

This design translates `HMS-NFR-01`–`HMS-NFR-14` and the approved Unit 3 functional rules into quality patterns for direct Spark clients using Hive Metastore (HMS) and RustFS. It retains the fixed local Compose proof of concept and the approved three-bucket role matrix. It does not implement or change authorization.

HMS metadata visibility and RustFS object authorization are separate. Apache Hive's storage-based authorization checks filesystem permissions; Apache Hadoop documents that S3A reports stub permission metadata and does not enforce authorization from those stubs. The user accepts cross-environment metadata visibility. Direct Spark data access must be authorized by RustFS; metadata DDL restrictions are not guaranteed.

## Identity consistency pattern

Every Spark operation carries two independent credentials:

- A Kerberos principal and ticket cache used for HMS Thrift authentication.
- RustFS S3 credentials used by the object client (S3A or Iceberg S3FileIO).

For a human session, both identities must map to the same canonical user and approved role. `write-service-account` is reserved for ETL and is never a fallback for a human request. The design records the authenticated identity at each boundary without logging tickets or keys. If identity correlation is missing, ambiguous, or inconsistent, the operation fails closed.

FreeIPA membership is the intended canonical role source after the separately approved cutover. MIT Kerberos remains authoritative until Unit 6; this design does not direct production callers to FreeIPA.

## Layered authorization pattern

```text
Caller validation
  ├─ HMS Thrift: Kerberos authentication → metadata response (visibility accepted)
  └─ RustFS S3: caller's S3 credentials → bucket IAM decision
                    │
            data requires RustFS allow
```

HMS metadata visibility and RustFS object operations are probed separately and then together through Spark. Cross-environment metadata visibility is accepted. The decisive result is whether Spark can fetch object data using that caller's own RustFS identity. A successful metadata lookup never implies permission to read data. Ranger is not in the direct Spark request path and does not enforce direct Spark object access.

The expected policy is:

| Role | HMS metadata visibility | RustFS object target |
|---|---|---|
| `developer-user` | All three environments | Read all; write only `lake-dev` |
| `analyst-user` | Production only | Read `lake`; no writes |
| `write-service-account` | All three environments | Read/write all three |
| `admin` | Existing administrator mapping | Existing administrator mapping |

Unknown, conflicting, or unresolvable role identity denies. The exact matrix and operation list are in the approved Functional Design.

## Bounded, fail-closed request pattern

Each dependency call has finite connect/read/request timeouts and a bounded retry policy. Retry only transient failures that are safe to repeat; authentication, authorization, invalid input, conflicting metadata, and unknown response shapes stop immediately. Timeouts and uncertain results are not interpreted as absence or allow. No request is retried under a broader service identity.

| Failure | Required outcome |
|---|---|
| Kerberos ticket missing, expired, or rejected | HMS operation denied; no alternate principal |
| Role absent, conflicting, or identity correlation fails | Deny before metadata/data request where possible |
| HMS unavailable or metadata decision indeterminate | Deny new operation; do not infer permission from RustFS success |
| RustFS unavailable or S3 request denied | Data operation fails; do not infer permission from HMS success |
| Unknown database/environment or unsafe location | Deny before write or mutation |
| Partial multi-step operation | Return incomplete/failure; do not report success or automatically undo unknown state |

Exact timeout/retry numbers and supported client behavior are Infrastructure Design and Build and Test decisions; this design does not invent an SLA.

## Environment and location validation pattern

New database roots are explicit:

- Production: `s3a://lake/warehouse/<database>/`
- Development, including `lhdev*`: `s3a://lake-dev/warehouse/<database>/`
- UAT: `s3a://lake-uat/warehouse/<database>/`

Table and partition locations must remain within their parent database's bucket boundary. Before any later authorized mutation, validate the observed HMS location against the approved environment mapping. Missing classification, implicit default, cross-bucket/external location, or conflict blocks the operation. Existing production database/table locations are read as preservation inputs and are never silently rewritten.

Because object stores are not POSIX filesystems, location validation does not stand in for an S3 policy decision. The S3 request still requires the caller's RustFS credentials and policy.

## Authorization cache and revocation pattern

No immediate revocation guarantee is assumed. Kerberos ticket lifetime, Spark/HMS client metadata caches, server-side identity/group caches, and RustFS policy propagation can produce different effective delays. Build and Test must measure the time from role removal or credential revocation until a new request is denied at each layer. The result must report the observed maximum for the tested setup and configuration.

Cache expiration or refresh failure must not broaden access. Active notebook termination and credential-cache destruction remain Unit 4 responsibilities. This Unit's result concerns new HMS/S3 requests only.

## Secret-safe observability pattern

Record enough to diagnose decisions without exposing credentials or data:

- Timestamp and bounded duration.
- Sanitized principal identifier and role resolution outcome.
- Environment/database/table classification and operation category.
- Enforcement layer (`Kerberos`, `HMS metadata`, or `RustFS object`).
- Allow/deny/error category and bounded reason.

Exclude passwords, S3 keys, keytabs, ticket contents, raw credentials, full request/response bodies, object names when not necessary, and object contents. Dependency errors are mapped to an allowlisted category rather than copied verbatim. Retain existing local container/application logs only; no separate audit service or retention SLA is designed.

## Preservation and recovery pattern

Before any future authorized change to HMS authorization or database locations, take a reviewed inventory of affected database/table locations and the relevant authorization configuration. Rehearse recovery against a disposable metastore and object store. No operation may automatically relocate or delete production data, and no rollback may overwrite state that has changed unexpectedly. If metadata is changed but object operations fail, classify the result as incomplete and require review.

## Verification and hard architecture gate

Tests use only disposable identities, databases, tables, and objects. Each test records the effective HMS principal, effective RustFS identity/policy, operation, environment, result, and denying layer without secret values. Positive and negative probes cover discovery, metadata listing, data reads, create/append/overwrite, drop/delete, unsafe locations, dependency failure, missing credentials, revocation delay, and preservation.

**RustFS object gate:** Run the matrix against the exact Hive/Spark/Iceberg/Hadoop S3A/RustFS versions. The analyst must read a populated production test table and receive an object authorization denial when Spark attempts to read populated dev/UAT test tables. Developer, analyst, and writer write behavior must match their RustFS policies. Cross-environment metadata visibility is accepted and is not evidence of data access. This does not guarantee analyst metadata DDL is denied; if that is required, seek separate architecture approval for an HMS authorizer.

## Requirement traceability

| Requirement | Design pattern |
|---|---|
| `HMS-NFR-01`–`02` | Fixed-scope operation, bounded calls, sanitized elapsed time |
| `HMS-NFR-03`–`05` | Fail-closed dependency handling, layered decisions, identity correlation |
| `HMS-NFR-06` | Measured cache and revocation delay |
| `HMS-NFR-07`–`10` | Isolated credentials, internal request path, least privilege, safe diagnostics |
| `HMS-NFR-11`–`12` | Preservation inventory, disposable recovery, safe failures |
| `HMS-NFR-13`–`14` | Pinned versions, disposable probes, readback and preservation evidence |

## Deferred implementation decisions

Infrastructure Design must specify only approved existing-component settings, protected mounts, network use, and concrete timeout/retry configuration. Build and Test must establish caller identity propagation, exact metadata/object authorization, cache/revocation behavior, failure classification, redaction, and preservation on the pinned stack. If metadata enforcement fails, any additional plugin, gateway, HiveServer2, service, or version change returns to architecture review before design or implementation.
