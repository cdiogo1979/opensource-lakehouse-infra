# Execution Plan — Repository Rename

## Detailed Analysis Summary
- **Transformation type**: configuration, documentation and an operational recreation; no code or behavior change.
- **Change impact**: the product file's repository URL (Airflow bundles and Jenkins jobs keep their names); container mounts move to the new folder; the notebooks' Initialization path.
- **Risk**: low to medium. The recreation interrupts open notebook servers; Airflow is recreated (bundles change). Rollback: the old URL still redirects; the stack can be recreated again.

## Workflow Visualization
```mermaid
flowchart TD
    Start(["User Request"])
    subgraph INCEPTION["INCEPTION PHASE"]
        WD["Workspace Detection<br/><b>COMPLETED</b>"]
        RA["Requirements Analysis<br/><b>COMPLETED</b>"]
        WP["Workflow Planning<br/><b>IN PROGRESS</b>"]
        SK1["Reverse Engineering, User Stories,<br/>Application Design, Units<br/><b>SKIP</b>"]
    end
    subgraph CONSTRUCTION["CONSTRUCTION PHASE"]
        SK2["Functional, NFR, Infrastructure Design<br/><b>SKIP</b>"]
        CG["Code Generation<br/><b>EXECUTE</b>"]
        BT["Build and Test<br/><b>EXECUTE</b>"]
    end
    subgraph DEPLOY["DEPLOY PHASE"]
        DH["Deploy<br/><b>PREPARE HANDOFF</b>"]
    end
    Start --> WD --> RA --> WP --> CG --> BT --> DH --> End(["Complete"])

    style WD fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style RA fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style WP fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style SK1 fill:#BDBDBD,stroke:#424242,stroke-width:2px,stroke-dasharray: 5 5,color:#000
    style SK2 fill:#BDBDBD,stroke:#424242,stroke-width:2px,stroke-dasharray: 5 5,color:#000
    style CG fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style BT fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style DH fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style Start fill:#CE93D8,stroke:#6A1B9A,stroke-width:3px,color:#000
    style End fill:#CE93D8,stroke:#6A1B9A,stroke-width:3px,color:#000
    linkStyle default stroke:#333,stroke-width:2px
```
Text alternative: Workspace Detection and Requirements Analysis are completed; Workflow Planning leads to Code Generation, Build and Test, and the Deploy handoff. Reverse Engineering, User Stories, Application Design, Units Generation, and the Functional, NFR and Infrastructure Design stages are skipped.

## Phases
- [ ] Reverse Engineering, User Stories, Application Design, Units Generation: SKIP. No new component, method or interface; the references were inventoried directly.
- [ ] Functional, NFR, Infrastructure Design: SKIP. No business logic; no new infrastructure.
- [ ] Code Generation: **EXECUTE** (one unit, `rename`): platform file, README and test; workload notebooks, README, AGENTS.md and test in the scratchpad clone (pushed on approval); the scratchpad remote.
- [ ] Build and Test: **EXECUTE**: host and workload suites; the stack recreated from the new folder (`start`, `start-airflow`) with no active run; the checks of requirements.md.
- [ ] Deploy: **EXECUTE**, as a handoff.

## Canonical Knowledge Impact Inventory
| Canonical path | Action | Requirement | Reason |
|---|---|---|---|
| `aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md` | UPDATE | FR-2, FR-6 | Five mentions of the workload repository's name |
| `aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/airflow-workflows.md` | UPDATE | FR-4, FR-6 | The repository name and the Initialization path |
| `aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/workload-python-environment.md` | UPDATE | FR-6 | One mention of the repository name |
| `aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/jenkins-ci-access.md` | RETAIN | none | No old name |
| `aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md` | RETAIN | none | No old name |
| `aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/starrocks-sql-access.md` | RETAIN | none | No old name |

The knowledge folder name (`opensource-lakehouse-infra-v2`) and the archives are retained unchanged.

## Success Criteria
- No container refers to the old folder; `default-main`/`default-uat` track `opensource-lakehouse-sample-dp`; UAT runs and Jenkins pass; JupyterHub works; the suites pass.
