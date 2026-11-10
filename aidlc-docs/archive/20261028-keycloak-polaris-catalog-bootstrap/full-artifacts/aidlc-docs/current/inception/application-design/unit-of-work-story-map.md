# Unit of Work Story and Requirement Map

## Story ownership and contribution

| Story | Primary unit | Supporting units | Coverage rationale |
|---|---|---|---|
| US-01 — Initiate creation of the default data product | U4 | U1, U2, U3 | CLI and coordinator provide the operator journey; provider units implement its effects. |
| US-02 — Provision environment-specific resources | U2 | U1, U3, U4 | Catalogs/namespaces live in Polaris; RustFS locations and CLI orchestration support them. |
| US-03 — Provision role groups and assign creator as owner | U2 | U1, U4 | Keycloak groups/identity and Polaris mapping/grants are configured and invoked by the bootstrap. |
| US-04 — Read all environments and write only to dev | U2 | U3, U4 | Polaris catalog privileges, vended storage scope, and integrated role tests. |
| US-05 — Read production without write access | U2 | U3, U4 | Production-only read grants, storage scope, and deny probes. |
| US-06 — Manage the product as owner | U2 | U3, U4 | Polaris product grants define authority; vended access follows grants; integrated tests protect admin boundaries. |
| US-07 — Write through automated service identity | U2 | U3, U4 | Writer OAuth identity and catalog grant; vended object access; Spark execution. |
| US-08 — Verify initial tables and safely repeat bootstrap | U4 | U1, U2, U3 | CLI orchestration and Spark verification exercise every provider and persisted state. |

Every story has one primary unit and all necessary supporting units; none is left unmapped.

## Requirement-to-unit coverage

| Requirement | Primary unit(s) | Supporting unit(s) |
|---|---|---|
| FR-01 — documented idempotent product CLI | U4 | U1, U2, U3 |
| FR-02 — three Polaris catalogs | U2 | U1, U4 |
| FR-03 — three namespaces | U2 | U4 |
| FR-04 — three RustFS buckets | U3 | U1, U4 |
| FR-05 — environment base locations | U3 | U2, U4 |
| FR-06 — four Keycloak groups | U2 | U1, U4 |
| FR-07 — writer OAuth identity | U2 | U4 |
| FR-08 — identity-to-Polaris mapping and owner | U2 | U4 |
| FR-09 — consistent metadata/storage access | U2, U3 | U4 |
| FR-10 — role access matrix | U2, U3 | U4 |
| FR-11 — smoke table in each namespace | U4 | U2, U3 |
| FR-12 — OIDC/OAuth and scoped storage credentials | U2, U3 | U4 |
| FR-13 — remove FreeIPA/Hive setup from default deployment | U1 | U4 |
| FR-14 — remove MIT Kerberos/KDC dependency | U1 | U4 |
| FR-15 — positive/negative role checks and safe rerun | U4 | U2, U3 |
| NFR-01 — idempotent and non-destructive | U4 | U1, U2, U3 |
| NFR-02 — local Compose and loopback admin interfaces | U1 | U4 |
| NFR-03 — persistent isolated metadata stores | U1 | U2 |
| NFR-04 — protected, nonlogged secrets | U1, U2, U3, U4 | — |
| NFR-05 — fail-closed authorization | U2, U3 | U4 |
| NFR-06 — pinned compatible versions | U1, U2, U3 | U4 |
| NFR-07 — safe readiness/errors | U4 | U1, U2, U3 |
| NFR-08 — property tests for pure functions/serialization | U4 | — |

## Coverage validation

- All eight approved stories US-01–US-08 have a primary unit and supporting units where needed.
- All functional requirements FR-01–FR-15 and non-functional requirements NFR-01–NFR-08 map to one or more units.
- Cross-provider authorization and storage credential behavior is deliberately shared by U2/U3 and verified end-to-end in U4.
