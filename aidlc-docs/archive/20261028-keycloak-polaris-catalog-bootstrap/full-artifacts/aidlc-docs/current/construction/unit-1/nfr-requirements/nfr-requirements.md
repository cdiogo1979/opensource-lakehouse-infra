# U1 NFR Requirements — Runtime Composition and Legacy Removal

## Scope

These requirements apply to the local Compose runtime foundation for the `default` data-product bootstrap. They refine approved project NFR-01–NFR-08 for runtime composition, readiness, persistence, recovery, local network exposure, and diagnostics. They do not define provider-specific authorization, storage vending, or the Spark bootstrap implementation owned by later units.

## Requirements

| ID | Requirement | Acceptance evidence | Trace |
|---|---|---|---|
| U1-NFR-01 | The supported default runtime targets one local operator and at most one bootstrap or smoke workload at a time. It has no horizontal scaling or concurrent-run guarantee. | Runtime documentation states the constraint; a second concurrent bootstrap is rejected or serialized by the owning workflow. | Q1; NFR-02 |
| U1-NFR-02 | Default startup/readiness must return a terminal result within a configurable 10-minute overall bound. Status is reported separately for each required provider, and timeout output identifies providers that are not ready. | With a provider held unready, startup/readiness exits within the configured bound and reports the provider; changing the bound is supported without source edits. | Q2; NFR-07 |
| U1-NFR-03 | Failed core containers may restart automatically under a bounded, configurable retry policy. Recovery must not restart healthy dependencies or delete persistent state. Exhausted recovery reports that operator action is required. | Failure injection shows retries stop at the configured limit, healthy providers remain running, persistent state is retained, and the terminal error is actionable. | Q3; NFR-01, NFR-07 |
| U1-NFR-04 | Identity and catalog metadata persist across ordinary restarts. The project documents an operator-managed backup and restore procedure for persistent state; this journey does not require scheduled backups. | Restart checks confirm identity/catalog metadata remains; documentation describes the backup and restore steps and their scope. | Q4; NFR-03 |
| U1-NFR-05 | Administrative host interfaces bind only to loopback. Provider-to-provider APIs are reachable through the private Compose network; only operator-required ports are published to the host. Plain HTTP is permitted only on loopback or the private local service network. | Compose configuration and host socket inspection show no non-loopback publications; service discovery works over the private network; no core provider API is exposed on a non-loopback host interface. | Q5; NFR-02 |
| U1-NFR-06 | Runtime status identifies each provider’s readiness and dependency impact. Startup and runtime diagnostics must be actionable and must redact credentials, tokens, and secret values. A separate monitoring or log-retention service is not required. | Deliberate provider failures produce status and nonzero dependent-operation results with actionable redacted messages; secret canaries do not appear in output/log checks. | Q6; NFR-04, NFR-07 |
| U1-NFR-07 | Core service metadata stores are isolated by owning service and persist across restart. New Keycloak and Polaris state must not reuse or import legacy FreeIPA, Hive Metastore, or KDC state. | Store ownership and mounts are documented; restart checks confirm persistence; static configuration/reference review confirms no legacy state is mounted into a new provider. | Functional Design; NFR-03, FR-13, FR-14 |
| U1-NFR-08 | Normal startup, restart, and product bootstrap must not delete persistent volumes or RustFS objects. Legacy cleanup is a separate explicit operation and may target only exact reviewed stores confirmed to belong to retired FreeIPA, Hive/metastore, or MIT KDC services. | Review startup/bootstrap paths for destructive volume/object operations; a cleanup dry run lists exact eligible resources and rejects ambiguous or unrelated stores. | Functional Design Q5; NFR-01 |
| U1-NFR-09 | Core images and client libraries are pinned to explicit compatible versions or immutable digests before implementation. The compatibility set is verified together before acceptance. | Version/compatibility matrix is recorded in Infrastructure Design; clean builds and integration checks use the pinned artifacts. | Approved project NFR-06 |
| U1-NFR-10 | The default runtime must not require FreeIPA, Hive Metastore/schema setup, MIT Kerberos, a KDC, keytabs, or `kinit`. Deferred Airflow, JupyterHub, Jenkins, and StarRocks integrations are not claimed as migrated or verified. | Default Compose dependency graph and active startup/client configuration contain no such dependency; deferred integrations are documented as opt-in and unsupported pending migration. | Functional Design; FR-13, FR-14 |

## Availability, performance, and recovery expectations

- This is a local single-machine developer environment. No uptime, throughput, latency, disaster-recovery, RTO, or RPO target is established by this unit.
- Default readiness has a bounded configurable 10-minute window. Individual service startup details and concrete retry/backoff values are implementation decisions for Infrastructure Design.
- Recovery is local and best-effort: bounded retries may recover a failed provider; after the retry limit, the operator receives a safe error and takes the next action.
- Manual backup/restore documentation is required for persistent identity/catalog state. Scheduled backup infrastructure and cross-host recovery are out of scope.

## Security and privacy expectations

- Administrative host access is loopback-only; provider APIs remain on a private Compose network unless a later approved requirement explicitly calls for a loopback host publication.
- Plain HTTP is limited to loopback and the private local service network. External/non-loopback exposure is outside this local runtime boundary.
- Secret files, tokens, credentials, and secret values must not appear in source control, diagnostics, or runtime logs; approved project NFR-04 applies.
- Failure or unavailable authorization providers must not cause dependent operations to proceed with fallback or stale access; approved project NFR-05 applies where authorization is exercised.
- No change to RustFS object data or unrelated persistent state is permitted during ordinary startup, failure recovery, or legacy cleanup.

## Verification approach

U1 verification belongs in Build and Test after implementation. It includes Compose validation, default-service inventory, readiness timeout/failure behavior, bounded restart behavior, persistence across restart, loopback binding inspection, secret-safe diagnostics, legacy dependency scans, and confirmation that normal startup paths contain no destructive volume/object cleanup. Object-level authorization and complete product bootstrap verification remain in U2–U4.
