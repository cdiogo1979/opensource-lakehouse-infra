# Unit 3 Infrastructure Design Plan — Hive Metastore and Direct Spark Authorization

## Unit and Approved Baseline

Unit 3 infrastructure design translates the approved Functional Design, NFR Requirements, and NFR Design into implementation-level choices for the existing Hive Metastore, Spark, and RustFS Compose setup. The approved behavior covers per-role metadata and object authorization, explicit environment locations, separate Kerberos and S3 identities, fail-closed handling, measured revocation, safe diagnostics, pinned versions, and preservation of production state.

The target boundaries are the existing Hive 3.1.3 metastore, Spark 3.5.5/Iceberg 1.8.1 clients, and RustFS 1.0.0. Current MIT Kerberos remains authoritative until Unit 6; FreeIPA remains isolated and no production identity cutover is included. `write-service-account` stays ETL-only and its broad S3 credentials must not be mounted into human contexts.

**Hard architecture gate:** Hive StorageBasedAuthorizationProvider relies on filesystem permissions; S3A's permission metadata is documented as stub data. The pinned stack's exact metadata behavior remains unverified. Infrastructure Design cannot claim this boundary works based on configuration alone. Build and Test must prove database/table/partition allow/deny using disposable state; if it fails, stop and request an architecture decision before implementing an alternate authorization component or changing versions.

## Infrastructure Design Checklist

- [x] Review approved Unit 3 Functional Design, NFR Requirements, and NFR Design; identify concrete infrastructure decisions still open.
- [x] Inspect existing HMS/Spark configuration, Compose networks, credential mounts, and pinned image versions without changing runtime state.
- [ ] Confirm whether implementation may modify existing Hive/Spark templates and service startup only, with no new service, plugin, HiveServer2, gateway, or host port: A recommended.
- [ ] Confirm identity-authority boundary for Unit 3 verification; preserve active MIT KDC and keep FreeIPA isolated until separately approved cutover: A recommended.
- [ ] Specify how disposable HMS metadata and RustFS objects/credentials are isolated from production state for later Build and Test: A recommended.
- [ ] Specify per-user Kerberos and RustFS credential inputs and private mount/cache boundaries; exclude writer credentials from human contexts: A recommended.
- [ ] Specify explicit environment-to-database warehouse settings, compatibility behavior for existing production locations, and default/cross-bucket rejection: A recommended.
- [ ] Specify bounded connection/request timeouts and retry classification without claiming a latency SLA: A recommended.
- [ ] Specify runtime permission, redaction, and evidence output requirements for authorization diagnostics: A recommended.
- [ ] Confirm no new host-published service ports, no production data movement, and no authority/policy mutations during design: A recommended.
- [ ] Generate `construction/unit-3/infrastructure-design/infrastructure-design.md` and `deployment-architecture.md` after this plan is approved.

## Infrastructure Questions

Complete each `[Answer]:` field. Recommended options preserve the approved PoC and security boundaries; choose `X` and describe a different choice if needed.

### Question 1 — Service and configuration scope

What infrastructure may Unit 3 change when implementation is later authorized?

A) Update only existing Hive/Spark configuration templates, database initialization/validation, and associated entrypoint/runtime settings. Add no service, plugin, HiveServer2, gateway, or host port. **(Recommended)**

B) Add a specifically named authorization service/plugin after documenting compatibility and deployment impact in `X`.

X) Other (describe exact services/configuration allowed).

[Answer]:A

### Question 2 — Identity authority during Unit 3

Which identity source may the Unit 3 implementation/test use before staged cutover?

A) Keep MIT KDC authoritative for existing runtime clients. Keep FreeIPA isolated; use only explicitly isolated test identities for tests that target FreeIPA. Do not change KDC aliases, production keytabs, or authority routing. **(Recommended)**

B) Cut production clients to FreeIPA as part of Unit 3.

X) Other (describe identity and authority boundaries).

[Answer]:A

### Question 3 — Test data and service isolation

How should later Build and Test isolate metadata and objects?

A) Use disposable databases/tables and unique probe objects under approved test paths; capture pre/post inventory and reject any operation that could relocate/delete existing production data. Isolate any required test credentials and ensure negative probes cannot touch production objects. **(Recommended)**

B) Create a separate disposable HMS/RustFS Compose stack for all tests; define network and storage isolation in `X`.

X) Other (describe test resources and preservation boundary).

[Answer]:A

### Question 4 — Per-user credential wiring

How should Spark receive identities when per-user sessions are exercised?

A) Supply each test/human context only its own Kerberos cache/keytab (as approved for that test) and RustFS credentials as protected read-only files/private cache mounts. Keep writer credentials restricted to ETL. Do not persist passwords or use environment literals. Jupyter session wiring itself remains Unit 4. **(Recommended)**

B) Introduce a credential broker or token service; describe the service and lifecycle in `X`.

X) Other (describe identity files, ownership, and lifecycle).

[Answer]:A

### Question 5 — Database location and compatibility

How should production, development, and UAT warehouse locations be applied?

A) Set explicit locations for new databases (`lake`, `lake-dev`, `lake-uat` roots). Preserve existing production locations. Validate existing DB/table/partition locations read-only first; stop on missing, ambiguous, external, cross-bucket, or conflicting locations. Never auto-relocate. **(Recommended)**

B) Normalize existing production locations to the new root during Unit 3; provide migration and rollback scope in `X`.

X) Other (describe mapping and compatibility rules).

[Answer]:A

### Question 6 — Timeouts and retries

What request behavior should be configured for identity, HMS, and RustFS calls?

A) Use finite connect/read/request timeouts and bounded retries for safe transient failures only. Never retry authentication/authorization/conflict errors or mutations under another identity; re-read state before a safe repeated mutation. Exact values are established and tested during implementation. **(Recommended)**

B) Specify exact timeout budgets and retry counts in `X`.

X) Other (describe call budgets and retry behavior).

[Answer]:A

### Question 7 — Diagnostics and audit data

What runtime evidence should infrastructure expose?

A) Use existing local logs and protected runtime output. Record timestamp, bounded duration, sanitized principal/role, environment/resource classification, operation, enforcement layer, outcome, and safe failure category; exclude credentials, tickets, raw payloads, and data contents. No new audit service or retention SLA. **(Recommended)**

B) Add a durable audit service/store; describe its access, retention, and network in `X`.

X) Other (describe output and retention).

[Answer]:A

### Question 8 — Network, version, and preservation boundaries

What deployment boundaries should remain in effect?

A) Keep existing internal Compose networks and pinned images/versions; add no published port, no dependency/service, no production data migration, and no identity or RustFS policy mutation during design. Any compatibility-driven architecture change returns for explicit review. **(Recommended)**

B) Allow named changes to networks, versions, ports, or data placement as described in `X`.

X) Other (describe deployment boundary).

[Answer]:A

## Answers and completion

The user requested continuation without providing alternate infrastructure choices. The plan's recommended answer A was applied to all eight questions: A/A/A/A/A/A/A/A. The infrastructure design and deployment architecture artifacts have been generated for review. The user later accepted cross-environment metadata visibility; direct Spark object authorization remains the verification gate.

## Design Constraints

- This plan authorizes design only. No service startup, test-data creation, configuration mutation, identity/policy change, database/location change, or production data access/mutation.
- Do not claim that configured StorageBasedAuthorizationProvider settings enforce database metadata authorization over RustFS/S3A until verified by pinned-stack tests.
- Do not add Ranger to the direct Spark/HMS/RustFS path or claim it protects S3 requests.
- Do not route human Spark sessions through the writer S3 identity.
- Preserve `lake` and every existing production database/table/object location; no migration or cleanup is in scope.
- Do not claim that analyst Hive metadata DDL is denied. Any requirement to restrict metadata mutation needs a separate architecture approval; direct Spark object access remains governed by RustFS.

## Approval Gate

The user selected the recommended defaults by requesting continuation. Review `construction/unit-3/infrastructure-design/` before Unit 3 Code Generation Planning. Unit 3 Build and Test requires a separate approved plan and must use disposable state for authorization probes.
