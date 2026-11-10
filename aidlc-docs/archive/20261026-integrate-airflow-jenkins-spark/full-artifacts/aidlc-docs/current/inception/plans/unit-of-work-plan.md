# Units Generation Plan — Airflow, Jenkins, and Spark Integration

## Purpose and Approved Scope

Application Design is approved. This plan decomposes the approved requirements, six user stories, and five design artifacts into implementation units. Existing component boundaries are the default. Units describe development ownership and sequence; they do not create new deployable services or authorize changes to application code.

The intent remains a local Docker Compose integration. Preserve the Hive/RustFS lakehouse, StarRocks, JupyterHub, data volumes, and existing writer credentials. Carry forward the Infrastructure Design item to verify the Spark master's advertised endpoint against the current worker startup URL (`spark://spark-iceberg:7077`) and Compose DNS.

## Execution Checklist

- [x] Read the approved execution plan and canonical knowledge impact inventory.
- [x] Map requirements, user stories, and Application Design components to existing ownership boundaries.
- [x] Resolve the decomposition questions below and check for contradictions. Answers A/A/A are clear and consistent.
- [x] Confirm the provisional units, sequencing, and coordination contract: four component-aligned units, sequential contract review, one maintainer.
- [x] Generate `aidlc-docs/current/inception/application-design/unit-of-work.md` with unit definitions and responsibilities.
- [x] Generate `aidlc-docs/current/inception/application-design/unit-of-work-dependency.md` with dependency matrix.
- [x] Generate `aidlc-docs/current/inception/application-design/unit-of-work-story-map.md` mapping every story to a unit.
- [x] Greenfield code organization strategy is not applicable; this is a brownfield project with established component directories.
- [x] Validate unit boundaries and dependencies and ensure every story is assigned. US-01 through US-06 map to the proposed units; US-02 and US-05 span the Airflow/Compose integration boundary as documented.
- [x] Request explicit approval of this plan before generating unit artifacts.
- [x] Validate generated unit definitions, dependency graph, and requirement/story coverage.
- [x] Request explicit review and approval of the generated unit artifacts.

## Existing Ownership Map

| Approved component / story area | Existing source boundary | Candidate unit |
|---|---|---|
| Existing Spark service and writer credential lifecycle (US-03) | `infra/spark/`, Spark configuration, existing Compose Spark service | Unit 1 — Spark writer runtime |
| Git Bundle store, DAG factory, per-run Spark driver (US-01, US-02, US-04, US-06) | Airflow bundle/DAG source reviewed during reverse engineering; destination paths to confirm before implementation | Unit 2 — Airflow bundle runner |
| Airflow/Jenkins service topology and Compose networking (US-02, US-05) | `docker-compose.yml`, new Airflow/Jenkins infrastructure configuration and image areas | Unit 3 — Platform Compose integration |
| Jenkins validation contract (US-05) | Jenkinsfile and CI validation source/configuration | Unit 4 — Jenkins validation |
| Retained Hive, KDC, PostgreSQL, RustFS, JupyterHub, StarRocks | Existing services and named volumes | No implementation unit; preserve and integrate through defined interfaces only |

## Provisional Unit Decomposition and Sequence

1. **Spark writer runtime** — initialize and renew the existing Kerberos writer ticket in the Spark service's private cache; expose the Spark submission and executor-access contract; retain the RustFS writer file-secret flow. Includes `US-03`. Infrastructure design must verify the master-advertised address and executor callback networking.
2. **Airflow bundle runner** — integrate the maintained Git Bundle/DAG factory source; pass the run-pinned bundle read-only to one ephemeral Spark driver per run; mount runtime credential files safely; report completion and clean up drivers on success or failure. Includes `US-01`, `US-02`, `US-04`, and `US-06`. Depends on Unit 1's Spark and writer runtime contract.
3. **Platform Compose integration** — integrate Airflow 3 services, its isolated PostgreSQL service/volume, Jenkins service, shared network, image/configuration build contexts, and host-visible bundle/credential paths. Preserve the selected Docker socket mounts and record their boundary. Coordinates Units 1 and 2; no existing lakehouse volume may be recreated or reset.
4. **Jenkins validation** — configure Jenkins to validate repository changes only and confirm it does not publish artifacts, deploy services, or move Bundle references. Includes `US-05`. Depends on the final repository paths and commands from Units 1–3.

This is a proposed sequential integration order. A shared interface contract may allow implementation tasks to proceed concurrently, but Compose integration and end-to-end verification depend on the Spark and Airflow contracts. Existing component boundaries remain authoritative; a unit does not imply a new service boundary.

## Decomposition Questions

Please fill each `[Answer]:` tag in this document. If an option does not fit, select X and describe your preference.

### Question 1 — Unit grouping

The proposed units follow the approved component boundaries and keep Jenkins validation separate from platform service wiring. Which decomposition should Units Generation use?

A) Use the four component-aligned units and sequence above.

B) Combine Units 3 and 4 into one platform integration unit because Jenkins changes are limited to CI configuration and Compose wiring.

X) Other (describe below).

[Answer]: A

### Question 2 — Cross-unit dependency handling

The Airflow runner depends on a stable Spark submission/credential contract. How should the plan handle implementation dependencies?

A) Keep the proposed sequential order; complete and review each unit's contracts before starting the next.

B) Keep the same units, but allow Spark, Airflow, and Compose work to proceed in parallel after documenting shared interface contracts; integrate in the proposed sequence.

X) Other (describe below).

[Answer]: A

### Question 3 — Ownership and coordination

No team or contributor split is specified in the approved requirements. What ownership model should the unit artifacts assume?

A) One maintainer owns the full integration; use unit boundaries for review and sequencing, with shared interfaces documented between units.

B) Separate owners may work on the units; include explicit handoff artifacts and interface review checkpoints between units.

X) Other (describe below).

[Answer]: A

## Category Assessment and Scope Constraints

- **Story grouping**: Relevant. Questions 1 and 2 ask whether to preserve the component-aligned split and proposed dependency sequence.
- **Dependencies/shared resources**: Relevant. The Spark master, writer identity, shared network, host-visible bundle checkout, and Docker socket are cross-unit contracts; Question 2 covers sequencing.
- **Team alignment**: Relevant because no contributor model is recorded; Question 3 asks how the plan should treat ownership and handoffs.
- **Technical/deployment considerations**: Established by approved requirements: local Compose, one local Spark cluster, preserved lakehouse volumes, and unconfigured UAT/production. No independent deployment targets or sizing requirements exist; no additional question is needed unless the answers change this scope.
- **Business domain boundaries**: Established by Application Design: Spark runtime, Airflow bundle orchestration, platform Compose, and Jenkins CI are distinct existing responsibilities. No new domain/service is proposed.
- **Code organization**: Greenfield-only question category; not applicable to this brownfield repository. New paths will be confirmed from the reviewed sibling source before implementation.

## Approval Gate

All answers are recorded and unambiguous. The four proposed units remain aligned to existing component boundaries. US-01 through US-06 are covered, with cross-unit stories explicitly identified. One maintainer owns the integration, and the work is sequenced with contract review between units. No scope or deployment assumptions changed.

**Status**: Plan approved; all three unit artifacts are generated and ready for review.
