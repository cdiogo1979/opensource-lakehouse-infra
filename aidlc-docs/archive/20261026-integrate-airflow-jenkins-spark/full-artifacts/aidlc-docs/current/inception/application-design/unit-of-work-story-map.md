# User Story to Unit Map — Airflow, Jenkins, and Spark Integration

## Story Assignment

| Story | Primary unit | Supporting unit(s) | Coverage rationale |
|---|---|---|---|
| US-01 — Run the intended bundle revision | Unit 2 — Airflow Bundle Runner | Unit 3 — Platform Compose Integration | Unit 2 resolves the pinned revision and supplies a read-only host-visible bundle; Unit 3 wires bundle storage and host paths. |
| US-02 — Submit a pinned workload to the target Spark cluster | Unit 2 — Airflow Bundle Runner | Units 1 and 3 | Unit 1 provides the driver/worker runtime and credential contract; Unit 2 creates a per-run driver/worker pair and submits; Unit 3 wires images, network, and mounts. |
| US-03 — Write lakehouse data as the configured writer | Unit 1 — Spark Writer Runtime | Unit 2 — Airflow Bundle Runner; Unit 3 — Platform Compose Integration | Unit 1 provides writer lifecycle for long-lived and ephemeral workers; Unit 2 supplies per-run driver/worker credentials; Unit 3 wires protected host files and service access. |
| US-04 — Understand and clean up a failed run | Unit 2 — Airflow Bundle Runner | Unit 3 — Platform Compose Integration | Unit 2 reports task result and owns driver cleanup semantics; Unit 3 supplies Docker/network/runtime wiring without touching lakehouse volumes. |
| US-05 — Validate workflow changes without publishing them | Unit 4 — Jenkins Validation | Unit 3 — Platform Compose Integration | Unit 4 owns the CI-only pipeline; Unit 3 adds Jenkins service, persistent home, network, and approved socket mount. |
| US-06 — Keep non-local environments unavailable until configured | Unit 2 — Airflow Bundle Runner | Unit 3 — Platform Compose Integration | Unit 2 owns explicit environment selection and fail-closed behavior; Unit 3 passes only configured local dev endpoints and keeps other targets unset. |

## Requirement Coverage Cross-Check

| Requirement | Primary unit(s) | Related stories |
|---|---|---|
| FR-1 — Compose integration | Unit 3 | US-02, US-05 |
| FR-2 — Workflow source and Git Bundles | Unit 2 | US-01 |
| FR-3 — Per-run driver and remote Spark execution | Unit 2; Unit 1 contract | US-02, US-04 |
| FR-4 — Writer identity on the per-run driver | Unit 2 | US-03 |
| FR-5 — Writer identity on target Spark workers | Unit 1 | US-03 |
| FR-6 — Jenkins scope | Unit 4; Unit 3 service wiring | US-05 |
| FR-7 — Bundle environments | Unit 2; Unit 3 configuration wiring | US-01, US-06 |
| FR-8 — Preserve the existing platform | Unit 3 integration constraint; all units must honor it | US-02, US-04 |
| NFR-1 — Credential handling | Units 1, 2, and 3 | US-03 |
| NFR-2 — Bundle immutability and run isolation | Unit 2; Unit 3 host path support | US-01, US-02, US-04 |
| NFR-3 — Scope and environment | Unit 1 and Unit 3 constraints | US-03 |
| NFR-5 — Docker control boundary | Unit 3; Unit 4 Jenkins boundary | US-02, US-05 |

NFR-4 is a partial property-based testing constraint rather than a user story. Identify applicable pure functions and serialization round-trips during per-unit design and Build and Test; this map does not assume that every unit has property-based test candidates.
