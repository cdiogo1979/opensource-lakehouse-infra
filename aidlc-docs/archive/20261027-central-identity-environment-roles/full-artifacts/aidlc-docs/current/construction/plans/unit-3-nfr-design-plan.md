# Unit 3 NFR Design Plan — Hive Metastore and Direct Spark Authorization

## Approved Baseline

The approved Unit 3 NFR requirements cover fixed PoC scale, bounded calls, fail-closed dependency behavior, independent identity consistency, measured revocation delay, per-user credential isolation, sanitized audit, pre-change preservation, pinned versions, and disposable verification. The approved functional design defines environment locations and a role matrix for direct Spark/HMS/RustFS access.

The S3A/HMS metadata authorization capability is unresolved, and the user accepts cross-environment metadata visibility. The NFR design must require per-user RustFS authorization for actual direct Spark reads and writes. It must not claim analyst metadata DDL restrictions; those require a separate architecture decision if later required.

## Design Checklist

- [x] Trace design patterns to `HMS-NFR-01` through `HMS-NFR-14` and approved Unit 3 functional rules.
- [x] Define logical responsibilities for caller identity binding, role/environment resolution, HMS metadata authorization, RustFS object authorization, failure classification, and sanitized audit.
- [x] Specify request flow showing separate Kerberos and RustFS identities and how each is correlated to the same approved role without credential fallback.
- [x] Define bounded-call, fail-closed, and retry behavior across identity services, HMS, and RustFS.
- [x] Define how database/table/partition locations are validated against approved environment roots without changing existing production locations.
- [x] Define revocation/cache measurement and how NFR design distinguishes measured behavior from target behavior.
- [x] Define secret isolation, redaction, diagnostics, and evidence handling.
- [x] Define preservation and recovery checkpoints before any future authorized metadata/location change.
- [x] Specify completion evidence and stop conditions for the unresolved HMS/S3A metadata gate.
- [x] Record version, service, and architecture constraints and deferred decisions for Infrastructure Design or Build and Test.
- [x] Generate `construction/unit-3/nfr-design/nfr-design-patterns.md` and `logical-components.md` after this plan is approved.
- [x] Present the NFR Design artifacts for explicit review before Unit 3 Infrastructure Design.

## Design Boundaries

- Planning and design only. Do not start or modify FreeIPA, MIT KDC, Hive Metastore, Spark, RustFS, or Compose services.
- Do not modify role membership, policies, credentials, keytabs, Hive grants, database/table locations, buckets, objects, or production data.
- Do not add Ranger to direct Spark requests or claim UI filtering as authorization.
- Do not introduce a plugin, gateway, HiveServer2, proxy, new service, or version change. If the pinned HMS provider fails the role metadata matrix, stop for an explicit architecture decision.
- Keep `write-service-account` ETL-only; human contexts must not receive its credentials as fallback.
- Use disposable databases/tables/objects and test identities for any later verification. No runtime probes are authorized by this design plan.
- Preserve existing production `lake` locations and objects; no automatic relocation, deletion, or destructive rollback.
- Infrastructure Design may specify existing-component settings, file/secret boundaries, and bounded timeouts only after this NFR Design is approved. New enforcement components remain an architecture decision.
- Build and Test must separately establish effective principal identity, S3 identity, role-based metadata and object allow/deny, cache/revocation timing, outage behavior, redaction, and preservation against the pinned versions.

## Approval Gate

The Unit 3 NFR Requirements and technology decisions were answered A/A/A/A/A/A/A/A using recommended options and approved by the user on 2026-10-27. The user approved this NFR Design Plan on 2026-10-27, and the NFR Design artifacts have now been generated. Review `construction/unit-3/nfr-design/nfr-design-patterns.md` and `logical-components.md` before Unit 3 Infrastructure Design. No implementation or runtime work is included.
