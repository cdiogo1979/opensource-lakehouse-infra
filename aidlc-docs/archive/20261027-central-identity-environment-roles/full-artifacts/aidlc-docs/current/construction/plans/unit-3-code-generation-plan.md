# Unit 3 Code Generation Plan — Hive Metastore and Direct Spark Authorization

## Unit Context

- **Unit:** Unit 3 — Hive Metastore and Direct Spark Authorization.
- **Stories:** US-03, US-04, US-05, US-06, and US-09 in `inception/application-design/unit-of-work.md`, covering production preservation, environment locations, and direct Spark metadata/object access.
- **Dependencies:** Approved Unit 3 Functional Design, NFR Requirements, NFR Design, and Infrastructure Design; existing Hive 3.1.3, Spark 3.5.5, Iceberg 1.8.1, and RustFS 1.0.0 configuration.
- **Implementation boundary:** Existing Hive/Spark templates, database initialization/location validation, and related existing startup settings only. No new service, plugin, HiveServer2, gateway, proxy, published port, version change, identity cutover, or production data movement.
- **Authority boundary:** MIT KDC remains authoritative. FreeIPA remains isolated. Do not create or change runtime identities, memberships, keytabs, RustFS policies, or credentials in Code Generation.

This plan is the source of truth for Unit 3 Code Generation. Do not add or run tests during Code Generation. All runtime/build tests and disposable authorization probes belong to the separately approved Build and Test plan.

## Approved Contracts

- Role matrix: `developer-user` reads all environments and writes only development; `analyst-user` reads production and cannot write; `write-service-account` reads/writes all environments for ETL only; preserve the existing `admin` mapping.
- New database roots are explicit: production `s3a://lake/warehouse/<database>/`, development (including `lhdev*`) `s3a://lake-dev/warehouse/<database>/`, and UAT `s3a://lake-uat/warehouse/<database>/`.
- Existing production database/table/partition locations and all objects are preserved. No automatic relocation, deletion, rewrite, or migration. Reject ambiguous, implicit, external, cross-bucket, conflicting, or out-of-root locations.
- Kerberos HMS authentication and RustFS object authorization are separate enforcement decisions. No writer credential or identity fallback is allowed for human contexts.
- Keep pinned service versions, internal Compose networks, and existing ports. Diagnostics are allowlisted and secret-safe. Requests use finite timeouts and only bounded safe retries.
- **Authorization boundary:** The user accepts cross-environment metadata visibility. The hard gate is that direct Spark/Iceberg reads and writes use per-user RustFS credentials and the RustFS role matrix prevents unauthorized object access. This does not guarantee HMS metadata DDL restrictions; do not claim analyst DDL is denied.

## Sequential Generation Steps

### Step 1 — Establish implementation baseline and safety boundary

- [x] Confirm the exact existing files and effective settings for HMS authorization, HMS/Spark Kerberos identity, Spark S3 client credentials, database initialization, and Compose mounts.
- [ ] Identify and document how the later approved Build and Test stage will capture production database/table/partition locations as read-only baseline evidence; do not query production or object contents during Code Generation.
- [x] Keep any test identity/configuration isolated from the live MIT KDC and normal RustFS service. Do not provision identities, credentials, or test resources in this stage.
- [ ] If necessary metadata and object isolation cannot be proven for later verification, stop and revise the Build and Test plan before runtime work.

### Step 2 — Add explicit environment location validation

- [x] Update only the existing database initialization/location code to derive the approved root from an explicit environment value and database name for the existing TPC-H ETL workload.
- [x] Reject missing/unknown environment, missing/duplicate/malformed database names, invalid S3A locations, bucket mismatch, cross-environment paths, and conflicting existing database/table locations before writing tables.
- [x] Read back and validate the ETL's existing database/table metadata without changing current production paths. Preserve recognized pre-existing production database locations exactly; reject other conflicts.
- [x] Keep UAT and development roots distinct; require an explicit `prod`, `dev`, or `uat` selection and explicit database list, with no environment fallback.
- [x] Keep the new location logic fail-closed and make errors safe to log.

### Step 3 — Preserve identity separation in existing Spark/HMS configuration

- [x] Keep Kerberos principal/cache selection distinct from S3 credential selection in the ETL workload and identify the effective principal in its protected run manifest.
- [x] Preserve the existing per-notebook credential mounts and ETL writer context; no writer/HMS/admin fallback was added to human-session credential selection.
- [x] Keep ETL writer credentials limited to the existing ETL service context; credentials, keytabs, mounts, and live identities were not changed.
- [x] Do not change JupyterHub per-user authentication/session delivery in this unit; that remains Unit 4.
- [x] Do not claim per-user metadata authorization based solely on `hive.metastore.execute.setugi`, Kerberos authentication, or configured StorageBasedAuthorizationProvider. Cross-environment metadata visibility is accepted by the user.

### Step 4 — Make only approved existing-template changes

- [x] Apply only the TPC-H loader code, its explicit Compose environment inputs, and operator invocation documentation required by Step 2 and allowed by the approved Infrastructure Design.
- [x] Retain current versions, services, internal network boundaries, ports, and active MIT KDC routing.
- [x] Do not add Ranger to direct Spark/HMS/RustFS, HiveServer2, a gateway, proxy, custom authorization plugin, new package/service, or alternate filesystem unless architecture is separately approved.
- [x] Do not generate changes that imply an unsupported metadata DDL authorization claim; record the limitation. Build and Test verifies data access at the RustFS boundary.

### Step 5 — Add safe diagnostics and verification hooks

- [x] Keep existing diagnostics safe and expose environment, target bucket/database, effective principal, and observed location in the protected workload manifest; no unsupported HMS authorization result is reported.
- [x] Exclude passwords, access/secret keys, keytabs, ticket contents, raw payloads, object contents, and unrestricted response bodies.
- [x] Provide deterministic environment/location validation in the ETL path and record its selected target in the protected manifest. Spark/RustFS object authorization remains a Build and Test gate.

### Step 6 — Review scope and prepare Build and Test handoff

- [x] Review every changed file against approved Unit 3 design artifacts and the no-new-service/no-cutover boundary.
- [x] Document changed files, effective identity flows, location rejection rules, remaining architecture gaps, and rollback/preservation constraints in a Unit 3 code summary.
- [x] Update plan checkboxes and `aidlc-state.md`; no tests were added or run during Code Generation.
- [x] Prepare a separate Build and Test Plan with disposable principals, metadata, object prefixes, positive/negative probes, before/after preservation checks, outage/revocation checks, timeout measurements, and log-redaction checks.
- [ ] Keep the object authorization result as a hard stop: if a role can read or mutate objects outside its RustFS scope, halt and request an architecture decision. Do not proceed to identity cutover.

## Build and Test Gates

The separately reviewed Build and Test stage must establish:

1. Existing production locations are unchanged and new database roots are explicit for prod, dev, and UAT.
2. Ambiguous, implicit, external, cross-bucket, conflicting, and out-of-root locations fail before mutation.
3. The effective Kerberos and RustFS principals are independently identified for each disposable role context; no human request uses writer/admin/HMS credentials as fallback.
4. The pinned Spark/Iceberg/RustFS stack enforces the object read/write matrix on disposable resources, including real Spark reads where metadata is visible but RustFS access is denied.
5. Failure, revocation/cache delay, finite timeouts, safe retry behavior, partial operations, and sanitized diagnostics meet the approved NFRs.
6. Pre/post inventories show no production database, location, bucket, object, identity, keytab, or policy changes.

If Gate 4 fails, stop. Do not cut over identities or claim the requested data authorization is implemented. Return to architecture review for a separately approved enforcement approach. This plan does not claim that Hive metadata DDL is restricted by role.

## Scope Exclusions

- No changes to the active MIT KDC, FreeIPA authority/cutover, users, role memberships, keytabs, S3 credentials, or RustFS IAM policies.
- No changes to Jupyter authentication or session credential delivery (Unit 4), StarRocks/Ranger authorization (Unit 5), or integrated authority cutover (Unit 6).
- No production database/table/partition relocation, object copy/delete, bucket mutation, or workspace change.
- No new service, gateway, proxy, HiveServer2, authorization plugin, host port, package, or image/version change without architecture approval.
- No tests or runtime probes during Code Generation; do not start services or create disposable resources in this stage.

## Approval Gate

Review this plan before Unit 3 Code Generation. Approval authorizes only the listed implementation scope; it does not waive the object authorization gate or authorize runtime mutations, testing, service startup, or identity cutover.
