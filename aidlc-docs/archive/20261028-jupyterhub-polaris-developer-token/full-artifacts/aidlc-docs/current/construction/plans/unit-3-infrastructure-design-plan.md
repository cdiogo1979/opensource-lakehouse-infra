# Unit 3 Infrastructure Design Plan — Polaris Authorization and RustFS Credential Vending

## Purpose

Map the approved Unit 3 authorization, short-lived credential, latency, and audit patterns onto the existing local Polaris/RustFS Compose stack. This stage selects configuration files, bindings, network reachability, and operational validation; implementation and provider changes remain out of scope until Code Generation is approved.

## Inputs

- `aidlc-docs/current/construction/unit-3/functional-design/`
- `aidlc-docs/current/construction/unit-3/nfr-requirements/`
- `aidlc-docs/current/construction/unit-3/nfr-design/`
- Existing `docker-compose.yml`, `infra/polaris/oidc.properties`, `infra/polaris/bootstrap-default-catalogs.py`, and `.runtime/container-mounts/polaris-application.properties`.
- Existing Polaris 1.8.0, RustFS 1.0.4, Spark 3.5.5, and Iceberg 1.8.1 pins.

## Infrastructure design work plan

- [x] Map the credential duration/cache targets to exact Polaris 1.8.0 properties and identify the approved source of runtime configuration.
- [x] Define network reachability for Polaris's management/metrics interface without publishing it to host or exposing it to Spark user containers.
- [x] Select bounded Polaris-to-RustFS STS request and connection-pool limits compatible with the two-user profile and five-second credential-vending target.
- [x] Preserve and verify the existing catalog-to-bucket mapping and table path convention `bucket/catalog/db/table`; ensure vended credentials remain within the authorized table location.
- [x] Define startup health checks and operator diagnostics for configuration validity, STS availability, and management metrics.
- [x] Map existing Compose networks, mounts, ports, and protected runtime files without introducing a monitoring service, credentials, or catalog/grant reset.
- [x] Generate `infrastructure-design.md` and `deployment-architecture.md` after clarification answers are resolved.
- [x] Validate traceability to the approved Unit 3 functional/NFR designs and identify pinned-version gaps before Code Generation.

## Clarification questions

**Answers recorded after user approval of the recommended options:**

- **Q1: A.** Put the verified non-secret Polaris duration/cache properties in the existing `.runtime/container-mounts/polaris-application.properties`, mounted read-only. Design targets: `polaris.features."STORAGE_CREDENTIAL_DURATION_SECONDS"=900` and `polaris.features."STORAGE_CREDENTIAL_CACHE_DURATION_SECONDS"=600`; verify exact parsing and behavior against the pinned image before applying.
- **Q2: A.** Bind Polaris management endpoints to container loopback, keep port 8182 unpublished and unavailable to Spark user containers, retain the in-container health check, and use `docker compose exec polaris ...` for operator diagnostics. Validate the exact host-binding property in the pinned image.
- **Q3: A.** Require a maximum 5-second end-to-end STS credential-vending deadline, bounded connection acquisition/connect/read timeouts, and a finite small connection pool sized for two users. Fail closed; do not add an unbounded queue or static credential fallback. Exact supported timeout/pool knobs are a pinned-image compatibility gate; do not assume an unsupported Polaris configuration key.
- **Q4: A.** Preserve the current catalog locations and verify resolved table paths and returned credential scope against the authorized table/object prefix and role operation. No catalog, grant, bucket, or data reset is included.

### Q1 — Runtime source for Polaris credential lifetime/cache

The current Polaris service mounts `.runtime/container-mounts/polaris-application.properties` read-only. Where should the approved 900-second credential duration and <=600-second cache values be configured?

A) Add the verified non-secret Polaris properties to the existing mounted runtime application-properties file; keep source-controlled defaults/examples free of secrets and preserve read-only mounting (Recommended; follows the current runtime-config boundary without a new service or config mechanism).

B) Put them in Compose environment variables.

C) Other configuration source (please specify).

### Q2 — Polaris management/metrics interface reachability

The Polaris management interface currently serves health and metrics on port 8182 and is not host-published, but Polaris also shares `data-access` with Spark user containers. How should we protect the management interface?

A) Bind the management interface to Polaris container loopback only, keep port 8182 unpublished, retain the in-container healthcheck, and let operators inspect metrics with `docker compose exec polaris ...`; do not add an admin sidecar or monitoring service (Recommended; user containers cannot reach unauthenticated management endpoints).

B) Keep it bound to all container interfaces and rely on the existing private Docker network; no host port is published.

C) Add a separate operator-only network/proxy for metrics (additional topology and service/configuration).

D) Other reachability design (please specify).

### Q3 — Polaris-to-RustFS STS bounds

Credential vending must meet a p95 target <=5 seconds and must fail closed under dependency saturation. What bounds should the local deployment use?

A) Configure a maximum 5-second end-to-end STS request deadline with bounded connection acquisition/connect/read timeouts and a small finite connection pool sized for the two-user profile; fail closed without an unbounded queue or static credential fallback (Recommended; aligns with the latency and concurrency targets while avoiding unverified numeric sub-timeouts).

B) Use library defaults for timeouts and connection pool sizing.

C) Other timeout/pool limits (please specify).

### Q4 — Storage location and credential-scope verification

Catalog storage configuration already maps each catalog to its environment bucket. How should infrastructure verification ensure the approved path and vending scope stay aligned?

A) Preserve catalog locations and verify the resolved table path follows `bucket/catalog/db/table`; verify vended credential scope covers only the authorized table/object prefix and role operation. Do not change catalog locations or reset data as part of this unit (Recommended; catches duplicate database segments and cross-environment scope leaks while preserving existing objects).

B) Recreate the catalogs and buckets during infrastructure changes so the paths are rebuilt from scratch.

C) Other verification boundary (please specify).

## Category analysis

- **Deployment environment:** Continue the existing single-host Docker Compose deployment; no cloud or multi-host topology is introduced.
- **Configuration:** Q1 resolves the non-secret Polaris runtime properties while keeping the current read-only mount pattern.
- **Networking:** Q2 resolves management-plane reachability; preserve Polaris REST access from approved Spark networks and RustFS S3/STS communication from Polaris.
- **Resilience/performance:** Q3 bounds STS calls and saturation; the five-second target remains to be measured, not assumed.
- **Storage:** Q4 preserves the approved three-bucket/catalog mapping and `bucket/catalog/db/table` layout; no data, catalog, or grant reset is authorized.
- **Operations:** Keep the existing healthcheck; document an operator-only way to inspect local metrics without opening a new host endpoint.
- **Secrets:** Do not put bootstrap/root values in Compose examples, logs, or user containers. No runtime secret file needs to be read or changed during this design stage.

## Next gate

Review `aidlc-docs/current/construction/unit-3/infrastructure-design/infrastructure-design.md` and `deployment-architecture.md`. Approve to continue to Unit 3 Code Generation planning, or request changes. This stage changes design documentation only; no application code, Compose configuration, provider settings, catalogs, grants, buckets, containers, or runtime data have been changed.
