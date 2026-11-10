# Unit 3 Infrastructure Design — Polaris Authorization and RustFS Credential Vending

## Scope and deployment assumptions

This design maps the approved Unit 3 authorization and credential-vending behavior onto the existing single-host Docker Compose stack. It keeps the pinned Polaris 1.8.0, RustFS 1.0.4, Spark 3.5.5, and Iceberg 1.8.1 versions. The design covers the maximum two-user local profile and preserves existing catalogs, grants, buckets, and data. It does not modify runtime configuration or start services.

The required flow remains: Spark submits the requesting user's Keycloak JWT to Polaris; Polaris validates identity and grants; Polaris requests short-lived storage credentials scoped to an allowed location from RustFS STS; Spark uses those credentials directly against RustFS.

## Polaris runtime configuration

Use the existing read-only mount:

| Host path | Container path | Access |
|---|---|---|
| `.runtime/container-mounts/polaris-application.properties` | `/deployment/config/application.properties` | Read-only |

The approved non-secret configuration targets are:

```properties
polaris.features."STORAGE_CREDENTIAL_DURATION_SECONDS"=3600
polaris.features."STORAGE_CREDENTIAL_CACHE_DURATION_SECONDS"=600
```

The cache duration remains shorter than the credential validity. Confirm the exact property syntax, startup acceptance, effective runtime values, and RustFS 1.0.4 STS support against the pinned images before adding these lines. The values are design targets, not yet applied settings or verified runtime outcomes. Do not put secrets in source-controlled examples or Compose environment declarations.

## Network and management-plane boundary

- Preserve Polaris's current `core` and `data-access` network attachments. Polaris needs its existing REST connections and RustFS STS/object-storage endpoint `http://rustfs:9000`.
- Preserve the host-published Polaris REST endpoint on loopback at `127.0.0.1:${POLARIS_HOST_PORT:-8181}`.
- The management/health/metrics listener on port 8182 must bind to `127.0.0.1` inside the Polaris container and must not be host-published. This prevents Spark user containers sharing `data-access` from reaching the unauthenticated management surface.
- Keep the current in-container readiness check against `http://127.0.0.1:8182/q/health/ready`.
- Operators inspect health and metrics through `docker compose exec polaris ...`; no monitoring sidecar, proxy, or metrics service is added.

The exact Quarkus management-host configuration key and its behavior must be verified in the pinned Polaris 1.8.0 image. If loopback binding breaks the bundled health check or is unsupported, stop and revise this design before relaxing management-plane isolation.

## Bounded STS requests and credential scope

- Enforce a maximum five-second end-to-end deadline for credential-vending requests, including STS connection acquisition, connection establishment, and response read.
- Use finite connection-pool capacity and bounded in-flight work appropriate for two concurrent users. Fail closed when the pool or STS dependency is saturated; do not add an unbounded wait queue.
- Do not use static, shared, root, bootstrap, or ambient storage credentials after a timeout or vending failure.
- Confirm exact supported timeout/pool controls for Polaris 1.8.0 and RustFS 1.0.4 before implementation. Do not invent or deploy unrecognized config keys. If the pinned components cannot enforce the end-to-end bound, record the gap and return for design review.
- Preserve the role operation matrix and catalog locations. Polaris must authorize the requested operation and resolved location before vending credentials. Vended storage permissions may cover only the authorized table/object prefix and required operation, never the whole bucket by default.

The intended object layout remains `bucket/catalog/db/table`. Expected examples are:

| Catalog | Namespace/database | Bucket | Table location pattern |
|---|---|---|---|
| `lakehouse` | `default_lh` | `bucket-default` | `s3://bucket-default/lakehouse/default_lh/<table>` |
| `lakehouse_uat` | `default_lhuat` | `bucket-default-uat` | `s3://bucket-default-uat/lakehouse_uat/default_lhuat/<table>` |
| `lakehouse_dev` | `default_lhdev` | `bucket-default-dev` | `s3://bucket-default-dev/lakehouse_dev/default_lhdev/<table>` |

These are verification expectations based on current bootstrap mappings; they are not a request to recreate or relocate any catalog or table.

## Health, diagnostics, and telemetry

- Retain Polaris's existing liveness/readiness checks and fail startup on invalid Polaris configuration.
- Use its existing management health and metrics surface for diagnostics. Confirm metric names and whether authorization and credential-vending durations can be measured separately in the pinned image.
- Operators use container-local diagnostics through `docker compose exec`; no new host port or user-network route is opened.
- Structured logs and metrics must preserve the approved redaction rules. Never include JWTs, authorization headers, RustFS temporary access/secret/session credentials, client secrets, request bodies, notebook content, or query text. Keep metric labels bounded and free of identity and table names.
- STS unavailability, timeout, unsupported duration, out-of-scope location, or credential refresh failure returns a safe fail-closed outcome without broadening credentials.

## Verification gates before implementation

1. Confirm Polaris 1.8.0 accepts and applies the duration/cache properties above.
2. Confirm RustFS 1.0.4 accepts the requested STS duration and enforces the returned location/operation scope.
3. Confirm the exact management listener host-binding configuration and that port 8182 is inaccessible from Spark and the host while the Polaris health check still passes.
4. Identify and validate pinned-version timeout/pool controls capable of meeting the five-second end-to-end STS deadline for two users.
5. Verify path resolution for all three existing catalog/database mappings and verify positive/negative vended-scope behavior without logging credential material.
6. Verify the pinned Polaris metrics support the approved separate latency measurements. Record a gap if they do not; do not claim the NFR target is measured.
7. Preserve the existing Iceberg 1.8.1 refresh and retry compatibility gates from the approved NFR design. No fallback credentials or mutation replay may be introduced to compensate for incompatibility.

## Traceability and limits

This design traces to Unit 3 functional authorization and credential-vending rules, approved NFR targets, and Unit 3 NFR design patterns. Unit 4 remains responsible for complete login-to-RustFS journey acceptance. Unit 2 live integration/performance and full Hub dependency-lock checks remain open and are not treated as passing evidence here.

No code, Compose file, provider setting, Polaris grant, catalog, bucket, container, or runtime data has been changed in this stage.
