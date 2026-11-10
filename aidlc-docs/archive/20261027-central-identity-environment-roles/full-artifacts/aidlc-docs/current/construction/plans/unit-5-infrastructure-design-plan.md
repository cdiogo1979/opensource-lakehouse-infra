# Unit 5 Infrastructure Design Plan — StarRocks Native LDAP Roles

## Superseding direction — 2026-10-28

The user replaced Ranger/UserSync with StarRocks native roles mapped from FreeIPA LDAP groups. The Ranger topology, policies, and questions preserved below are historical decision records and are not the approved design or current acceptance scope. Current architecture is documented in `construction/unit-5/infrastructure-design/`.

The approved/current test topology is the disposable StarRocks LDAP FE/BE plus isolated FreeIPA. The Hive Iceberg external-catalog matrix and writer MV refresh were verified using temporary isolated Hive Metastore/RustFS services; those services, volumes, and test credentials were removed afterward. No production service was attached or modified. No Ranger Admin, UserSync, or policy database is required.

The remaining deployment boundary is review of existing default/production FE grants and preparation of a separate production migration/rollback plan. The guarded test bootstrap must not be pointed to production.

## Historical Ranger infrastructure design (superseded)

## Unit and approved baseline

Unit 5 adds Ranger-backed SQL authorization to StarRocks OSS 4.1.6. FreeIPA is the identity and group source; Ranger UserSync reads approved groups; Ranger Admin stores policies; StarRocks FE evaluates SQL requests as the human principal. StarRocks' FE/BE service identity separately accesses Hive Metastore and RustFS after authorization. Direct Spark access remains governed by per-user RustFS credentials and is outside Ranger.

The approved Unit 5 NFR and design artifacts are in `construction/unit-5/nfr-requirements/` and `construction/unit-5/nfr-design/`. Ranger 2.9.0 is an evaluation candidate only. Its exact compatibility with StarRocks 4.1.6, including the plugin artifact, service definition, LDAP group handling, catalog resources/actions, cache/outage behavior, and revocation, remains unverified.

The existing optional StarRocks Compose services use the `iceberg-poc-net` network and named FE/BE data volumes. Those services, their volumes, the production RustFS, existing HMS metadata, active MIT KDC, FreeIPA state, identities, and policies must be preserved. The NFR-approved compatibility test boundary is disposable Ranger state, disposable StarRocks FE/BE state, and synthetic data. This plan must resolve whether synthetic catalog/object dependencies also need their own disposable services before implementation.

## Infrastructure design checklist

- [x] Review approved Unit 5 Functional Design, NFR Requirements, NFR Design, and technology decisions.
- [x] Inspect the existing Compose profile/network/volume boundaries for FreeIPA validation, StarRocks, Hive Metastore, and RustFS without changing runtime state.
- [x] Confirm the isolated test topology for Ranger Admin, UserSync, and a separate Ranger database; do not reuse HMS or Airflow metadata databases: A.
- [x] Confirm the isolated compatibility stack needs its own disposable Hive Metastore and RustFS and synthetic metadata/objects: A.
- [x] Define dedicated internal networks and explicitly exclude production `iceberg-poc-net`, production RustFS, and existing StarRocks volumes from experimental Ranger/UserSync paths: A.
- [x] Choose an isolated FreeIPA test instance/state on a dedicated network; do not use production FreeIPA: A.
- [x] Specify disposable StarRocks FE/BE names, images, volumes, and opt-in profile, separate from current StarRocks services: A.
- [x] Select no host ports by default; require explicit opt-in localhost-only binds for interactive access: A.
- [x] Require verified official artifacts, exact pins/digests, and plugin/service-definition checksums after compatibility evidence; exclude default credentials: A.
- [x] Define read-only CA/secret mounts, validated TLS where supported, finite health dependencies, and protected rotating local audit storage: A.
- [x] Define opt-in preflight, unique test-prefixed resources, isolated backup/restore, and inventory-checked teardown: A.
- [x] Generate `construction/unit-5/infrastructure-design/infrastructure-design.md` and `deployment-architecture.md` for review.

## Infrastructure questions

The user approved the recommended option A for all ten questions on 2026-10-27. The answer fields below record those decisions. These answers authorize only the isolated test stack and its synthetic data.

### Question 1 — Ranger Admin database

Where should Ranger's policy metadata live in the test topology?

A) Use a dedicated test database service and named volume, with its own credentials and health check. Do not reuse Hive Metastore, Airflow, or any existing database/schema. **(Recommended)**

B) Use a separately isolated database/schema on an existing database server; document exact server, isolation, backup, and credential boundaries in `X`.

X) Other (describe database, storage, and isolation).

[Answer]: A — dedicated Ranger test database service and volume, with independent credentials and health check.

### Question 2 — Synthetic catalog and object dependencies

How should the compatibility stack obtain Hive catalog metadata and query data?

A) Add disposable test-only Hive Metastore and RustFS services with separate test databases, buckets, credentials, networks, and volumes. Load only synthetic metadata and rows/objects. **(Recommended)**

B) Reuse specified existing services in a read-only and prefix-scoped manner; identify every endpoint, identity, object prefix, metadata namespace, and cleanup safeguard in `X`.

X) Other (describe the exact synthetic data path).

[Answer]: A — disposable HMS and RustFS services, separate test DB/bucket/credentials/volumes, synthetic-only data.

### Question 3 — Network boundaries

Which network layout should isolate the test stack?

A) Create dedicated internal-only Ranger control and synthetic lakehouse networks. Attach each service only to the networks it needs; do not attach experimental Ranger/UserSync or disposable StarRocks to `iceberg-poc-net`, production RustFS, JupyterHub, Airflow, or production FreeIPA. **(Recommended)**

B) Reuse named existing networks with a documented service-to-service reachability matrix and verified boundaries in `X`.

X) Other (describe networks and permitted flows).

[Answer]: A — dedicated internal Ranger-control, FreeIPA-test, and synthetic-lakehouse networks; no production network attachments.

### Question 4 — FreeIPA source for compatibility tests

How should Ranger UserSync receive test groups?

A) Use an isolated FreeIPA test instance/state reachable only on a dedicated internal network shared with UserSync. Do not use production FreeIPA; do not change existing validation identities or memberships without an approved test plan. **(Recommended)**

B) Use the existing FreeIPA validation instance with a dedicated test-only account/group and a narrowly scoped network attachment; document its effect on the current validation profile in `X`.

C) Use a synthetic LDAP fixture for Infrastructure Design/build checks, and defer live group-sync compatibility to a separately approved isolated test.

X) Other (describe the LDAP endpoint, account scope, and network).

[Answer]: A — isolated FreeIPA test state and a dedicated internal UserSync path, separate from production and current validation state.

### Question 5 — Disposable StarRocks topology

How should StarRocks compatibility testing avoid the current FE/BE state?

A) Define separate disposable FE/BE services with unique service/container names, separate named volumes, and the approved 4.1.6 image digests. Run them only in an explicit test profile; never use the current FE/BE volume names or recreate the existing services. **(Recommended)**

B) Use an isolated temporary Compose project with uniquely prefixed resources and no shared data mounts; document the project name and lifecycle in `X`.

X) Other (describe how service and storage collisions are prevented).

[Answer]: A — unique disposable FE/BE service names and volumes, StarRocks 4.1.6 image digests, explicit opt-in profile.

### Question 6 — Host exposure

Which endpoints should the isolated test publish?

A) Publish no ports by default. If interactive verification requires Ranger UI or StarRocks SQL access, bind only to `127.0.0.1` with explicit opt-in test configuration; never publish LDAP, Ranger internal, database, or BE ports. **(Recommended)**

B) Publish named endpoints on a controlled host interface; define access restrictions and firewall requirements in `X`.

X) Other (describe port bindings and access controls).

[Answer]: A — no host ports by default; optional explicitly enabled localhost-only UI/SQL binds; no LDAP/database/BE ports.

### Question 7 — Images and artifact integrity

How should Ranger/UserSync, database, and StarRocks integration artifacts be packaged?

A) Use exact releases only after StarRocks 4.1.6 compatibility evidence. Build or select reproducible test images from verified official release artifacts; pin base/image digests and plugin/service-definition checksums. Do not use floating tags or example default credentials. **(Recommended)**

B) Use named upstream container images for this disposable test only; record publisher, exact tag and digest, security limitations, and replacement path in `X`.

X) Other (describe sources, pins, and verification).

[Answer]: A — exact verified releases and official artifact integrity, pinned image/base digests and plugin/definition checksums; no floating tags/default credentials.

### Question 8 — TLS, secrets, health, and audit storage

How should internal credentials and dependencies be wired?

A) Mount CA material and service credentials as read-only protected files; validate LDAP/Ranger TLS where supported; use finite health checks and readiness dependencies; write sanitized Ranger/StarRocks test audit to a dedicated protected rotating local volume. No secret values in environment literals, arguments, or logs. **(Recommended)**

B) Use another named secret/certificate/audit system; define ownership, rotation, access, and startup failure behavior in `X`.

X) Other (describe TLS, secret, readiness, and audit handling).

[Answer]: A — read-only protected CA/secret mounts, TLS validation where supported, bounded health checks, protected rotating local audit volume.

### Question 9 — Test profile and lifecycle

How should operators start and remove the compatibility environment?

A) Keep all new services behind a clearly named opt-in test profile or separate Compose file. Require preflight checks for unique names/volumes/networks and verified synthetic targets; teardown removes only resources bearing the test-specific prefix after an inventory check. **(Recommended)**

B) Use a different lifecycle mechanism with equivalent collision, preflight, and cleanup controls documented in `X`.

X) Other (describe start, preflight, and cleanup behavior).

[Answer]: A — opt-in separate test profile/project, collision preflight, test-specific resource names, inventory-gated teardown.

### Question 10 — Ranger backup and restore

How should test policy state be recovered?

A) Export Ranger service definitions and policies and protect a database snapshot before test mutations; rehearse restore only into the isolated test database/volume. No production rollback automation or retention SLA. **(Recommended)**

B) Use a different isolated backup mechanism with restore evidence and boundaries defined in `X`.

X) Other (describe backup/restore and preservation).

[Answer]: A — export service definitions/policies and snapshot Ranger's dedicated test DB before mutation; restore only to isolated state.

## Design constraints

- This plan authorizes infrastructure design only. Do not edit Compose, build or pull images, start/stop services, create identities/policies/grants, mutate bucket/catalog contents, or run compatibility tests.
- Never connect experimental Ranger/UserSync to production FreeIPA, production RustFS, existing StarRocks FE/BE volumes, or production objects.
- Preserve the current StarRocks 4.1.6 FE/BE services and named volumes. Do not change pinned images or Ranger candidate selection without exact compatibility evidence and the required approval.
- Do not use Ranger Solr, HA services, public ports, Kerberos-authenticated Ranger, JavaScript policy conditions, or the optional StarRocks service-definition autocomplete plugin unless a later reviewed design shows they are required and compatible.
- Do not put FreeIPA directory administrator credentials in Ranger UserSync. Use only a scoped read-only test identity.
- Keep the requesting SQL principal separate from StarRocks' HMS/RustFS service identity. Ranger does not authorize direct Spark-to-RustFS access.
- Never use sample/default component passwords. No secret contents may be written to documentation, source, normal environment values, or command output.
- Exact StarRocks/Ranger compatibility, catalog/action mapping, group propagation, outage/cache semantics, and revocation behavior remain Build and Test gates.
- Production FreeIPA deployment, production RustFS policies, StarRocks grants, consumer migration, and MIT KDC transition remain separately gated by the approved production cutover plan.

## Approval gate

The user approved all recommended answers and requested continuation to Code Generation and Build and Test on 2026-10-27. The generated design records that authorization for isolated, test-only implementation and verification. It does not authorize production connectivity, production identity/policy/SQL-grant changes, KDC transition, or modification/removal of existing service data.

## Superseding direction — 2026-10-28

The user has replaced the Ranger approach with StarRocks native roles/grants mapped to FreeIPA LDAP groups. This amendment supersedes the Ranger-specific topology, backup, service, and compatibility requirements above. See `construction/unit-5/infrastructure-design/infrastructure-design.md`, `deployment-architecture.md`, and `construction/plans/unit-5-code-generation-plan.md` for the current approach. Existing test-only Ranger artifacts/state are retained as historical work and are not part of the target design. No production access or changes are authorized by this amendment.
