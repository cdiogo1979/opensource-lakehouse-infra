# Unit of Work Definitions — Keycloak + Polaris Bootstrap

## Delivery model

This is a brownfield implementation in one repository and one Docker Compose project. The units are development and verification checkpoints, not separately deployed microservices or team ownership boundaries. Work follows U1, then U2 and U3 in parallel where practical, then U4 integration. U2/U3 must agree on storage paths, principal-role names, authorization semantics, and credential-vending settings before U4 end-to-end integration.

Preserve the repository’s existing `infra/`, `scripts/`, root Compose, and `aidlc-docs/` layout. Place provider-specific configuration and helpers under `infra/keycloak/`, `infra/polaris/`, and existing `infra/bucket-init/` or a clearly named RustFS directory. Place the operator CLI/coordinator under `scripts/`. Keep the Spark smoke workload in the existing Spark area. Remove FreeIPA, Hive, and MIT Kerberos setup only after checking active references and removing dependent config. Keep unrelated Airflow, JupyterHub, Jenkins, and StarRocks components opt-in and outside the default journey; do not claim they are migrated.

## Unit definitions

### U1 — Runtime composition and legacy removal

**Purpose:** Provide the local runtime foundation for the approved journey and remove retired identity/catalog dependencies from the default stack.

**Scope:**
- Compose service graph and default/opt-in lifecycle for Keycloak, its supported persistent database, Polaris, dedicated Polaris PostgreSQL, and RustFS.
- Health/readiness and internal networking needed by later units.
- Persistent volumes for Keycloak, Polaris metadata, and object storage; no implicit volume deletion.
- Remove FreeIPA, Hive Metastore/schema initialization and MIT KDC/Kerberos requirements from the target default deployment and dependent client configuration.
- Preserve unrelated deferred services under opt-in profiles.

**Primary requirements:** FR-13, FR-14; NFR-02, NFR-03, NFR-06.
**Stories:** Supports US-01, US-02, US-08; infrastructure prerequisite for US-03–US-07.
**Dependencies:** None.
**Exit evidence:** Compose config validates; only journey-required long-running services start by default; services become healthy; persistent state survives restart; no active default dependency requires FreeIPA, Hive, or Kerberos.

### U2 — Identity and catalog authorization

**Purpose:** Establish Keycloak identities/groups and Polaris catalog/RBAC behavior for the product role model.

**Scope:**
- Keycloak realm/client/group configuration for `role-default-developer`, `role-default-analyst`, `role-default-owner`, and `role-default-writer`.
- Dedicated non-interactive writer OAuth identity and initial creator owner membership. Human accounts remain provisioned separately.
- Keycloak OIDC token claim configuration and Polaris principal resolution/role mapping.
- Polaris principals, principal roles, catalog roles, catalogs, namespaces, grants, and authorization verification.
- Role-specific catalog behavior for production, dev, and UAT.

**Primary requirements:** FR-02, FR-03, FR-06–FR-08, FR-10 (catalog portion), FR-12 (OAuth), NFR-04–NFR-06.
**Stories:** US-02, US-03, US-04, US-05, US-06, US-07.
**Dependencies:** U1. May proceed in parallel with U3 after interface agreement.
**Exit evidence:** Keycloak groups and writer identity exist; OAuth/OIDC claims resolve to the expected Polaris principals/roles; catalog operations pass and fail per the approved matrix; no product role receives realm administration.

### U3 — Object storage and credential vending

**Purpose:** Provide environment-isolated RustFS buckets and connect Polaris authorization to scoped, temporary object-storage credentials for Iceberg clients.

**Scope:**
- Create/validate `bucket-default`, `bucket-default-dev`, and `bucket-default-uat`.
- Configure namespace-scoped locations `default_lh/`, `default_lhdev/`, and `default_lhuat/`.
- Use protected platform bootstrap credentials for bucket/storage provisioning; do not issue ordinary users direct S3 credentials.
- Configure and verify Polaris-to-RustFS storage integration, including vended credential and refresh behavior supported by pinned versions.
- Validate access to data through Polaris-aware Iceberg clients and denial of raw S3 calls without a vended credential.

**Primary requirements:** FR-04, FR-05, FR-09, FR-10 (storage portion), FR-12 (STS/vending), FR-15 (storage checks), NFR-04–NFR-06.
**Stories:** US-02, US-04, US-05, US-06, US-07, US-08.
**Dependencies:** U1. May proceed in parallel with U2 after catalog/location and role contract agreement.
**Exit evidence:** Buckets and base locations match the environment map; vended credentials are short-lived and location/operation scoped; environment-crossing operations fail; users cannot access RustFS directly with static credentials.

### U4 — Bootstrap CLI and Spark verification

**Purpose:** Deliver the platform-admin experience and integrate the provider units into one safe bootstrap journey.

**Scope:**
- Host CLI command for creating/verifying the `default` product.
- Ordered, idempotent coordinator and provider adapters with redacted progress/errors.
- One-shot Spark job authenticating as writer through OAuth and using Polaris Iceberg REST plus credential vending.
- Create/validate `bootstrap_smoke_test` with deterministic schema and row in all three namespaces.
- Positive/negative role matrix checks, safe rerun/conflict behavior, and concise operator documentation.

**Primary requirements:** FR-01, FR-07, FR-11, FR-15, NFR-01, NFR-04, NFR-05, NFR-07, NFR-08.
**Stories:** US-01–US-08 (end-to-end integration; principal story ownership is mapped in `unit-of-work-story-map.md`).
**Dependencies:** U1, U2, and U3. The U2/U3 contract checkpoint is required before integration.
**Exit evidence:** Clean bootstrap creates or validates all required resources; all three smoke tables have expected row and path; positive and negative checks pass for each role; second run is non-destructive; conflicting state fails safely; output contains no secret values.

## Cross-unit contracts

| Contract | Owning unit | Consumers |
|---|---|---|
| Compose service names, endpoints, health conditions, networks, secret mounts, and volume names | U1 | U2, U3, U4 |
| Keycloak group and writer identity names; token issuer/audience/claim path; principal-role mapping | U2 | U4; U3 only where storage integration needs role context |
| Polaris catalog/namespace names and catalog-role/grant matrix | U2 | U3, U4 |
| Bucket names, S3 endpoint, region/path-style settings, and namespace base locations | U3 with U2 | U2, U4 |
| Vended credential delegation and refresh behavior | U3 with U2 | U4/Spark |
| Product spec, CLI result schema, step status/error redaction contract | U4 | operator and tests |

## Global non-goals

- Migrating existing data or automatically deleting resources, volumes, or bucket objects.
- Adding Ranger or any separate long-running bootstrap API/UI.
- Migrating Airflow, JupyterHub, Jenkins, or StarRocks in this increment.
- Issuing end-user long-lived S3 access keys.
