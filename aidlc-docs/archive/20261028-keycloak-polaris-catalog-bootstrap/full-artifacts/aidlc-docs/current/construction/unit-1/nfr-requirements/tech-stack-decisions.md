# U1 Tech Stack Decisions — Runtime Composition and Legacy Removal

## Decision record

| Area | Decision/constraint | Rationale and boundary |
|---|---|---|
| Runtime orchestration | Docker Compose on one developer machine. | Required by approved NFR-02; no cluster orchestrator or horizontal scaling is introduced in U1. |
| Identity provider | Keycloak replaces FreeIPA for the new journey. | Approved intent. U1 owns its runtime and persistent-state boundary; realm, OIDC claims, and group mapping are detailed by U2. |
| Iceberg catalog | Apache Polaris replaces Hive Metastore. | Approved intent. Polaris uses dedicated persistent metadata storage; catalog/RBAC behavior is detailed by U2. |
| Polaris metadata store | A dedicated PostgreSQL service/database separate from Keycloak and retired Hive metadata. | Approved NFR-03 and Application Design; concrete service/database names are set in Infrastructure Design. |
| Keycloak persistence | A supported persistent production-mode database configuration, isolated from Polaris metadata. | Approved NFR-03. The exact supported database/image combination is selected and pinned in Infrastructure Design. |
| Object storage | Existing RustFS component remains the object-storage provider for this journey. | Approved product design and FR-04/FR-05. Bucket provisioning and scoped credential/policy behavior are owned by U3. |
| Service networking | Private Compose network for provider APIs; only required operator-facing ports may be published on loopback. | Approved NFR-02 and U1 NFR-05; prevents non-loopback host exposure by default. |
| Persistent storage | Separate persistent stores for Keycloak, Polaris PostgreSQL, and RustFS. | Supports service isolation and persistence while preventing legacy-state import. Exact volume names and mount definitions belong to Infrastructure Design. |
| Legacy components | FreeIPA, Hive Metastore/schema initialization, MIT Kerberos/KDC, and active client dependencies are removed from the default journey after reference review. | Approved FR-13/FR-14 and U1 Functional Design. Immutable AI-DLC history may retain historical references. Deferred services are not represented as migrated. |
| Health and recovery | Service-scoped readiness with a configurable bounded startup window and bounded failed-container restart policy. | Required by U1 NFR-02/U1 NFR-03. Health commands, restart counts, backoff, and Compose syntax are Infrastructure Design decisions. |
| Images and libraries | Pin explicit versions or immutable digests and verify the set together. | Required by approved NFR-06. No version numbers are chosen in this NFR Requirements stage; compatibility is established during Infrastructure Design and Build and Test. |
| Bootstrap and Spark | On-demand host CLI and one-shot Spark job; not default long-running runtime services. | Approved U1 scope and U4 ownership. U1 provides runtime dependencies/readiness only. |
| Deferred integrations | Airflow, JupyterHub, Jenkins, and StarRocks remain opt-in and unsupported until separately migrated. | Prevents an unsupported legacy Hive/Kerberos dependency from being mistaken as part of the new journey. |

## Decisions deliberately deferred

- Exact image tags/digests, base distributions, and library versions.
- Exact Compose service names, profiles, ports, health-check commands, networks, and volume names.
- PostgreSQL image/database/user details and Keycloak database compatibility selection.
- Container restart counts/backoff and per-service health-check intervals.
- The implementation and invocation interface for the separate legacy-volume cleanup operation.

These choices belong in U1 Infrastructure Design and must satisfy the NFRs in `nfr-requirements.md`. No runtime package or service has been changed by this decision record.
