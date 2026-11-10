# Unit of Work Plan — Airflow Polaris Writer Identity

## Context and approved design

The approved design adds an Airflow writer token broker and coordinates it with a common Spark runtime/token-renewal provider. Spark runtime/provider code is shared by Jupyter and Airflow, but identity and renewal adapters remain separate. The two Bundle names, refs, and selection behavior stay unchanged. Runtime E2E remains limited to the main/production workflow.

The design approval selects Q4=A (common pinned runtime and renewal provider) and Q5=B (compatible Iceberg auth-provider upgrade preserving the initial-token handoff). The exact Spark/Iceberg release pin remains for Functional Design.

## Existing component and canonical-path mapping

| Requirement/work item | Existing component boundary | Canonical/design reference | Proposed unit |
|---|---|---|---|
| Airflow Compose services, writer secret custody, writer broker, run registration/revocation | Airflow control plane and Airflow writer token broker | `application-design/components.md`, `application-design/services.md`; v2 infra repo | Unit 1 — Airflow writer identity and broker |
| DAG-run setup/cleanup and unchanged Bundle selection | Airflow control plane / Bundle integration | `application-design/services.md`; `opensource-lakehouse/dags/dag_factory.py` | Unit 1 — Airflow writer identity and broker |
| Shared Spark/Iceberg runtime and token-provider implementation | Shared Spark runtime and provider | `application-design/components.md`, `component-methods.md`; shared across repositories/images | Unit 2 — Shared Spark runtime and identity adapters |
| Jupyter user adapter and Airflow writer adapter | Identity-specific adapters of shared runtime | `application-design/component-dependency.md`; v2 Jupyter and workload Spark sources | Unit 2 — Shared Spark runtime and identity adapters |
| Main-only E2E, UAT source/config check, Bundle validation, release evidence | Cross-unit integration verification | Requirements NFR-4 and approved execution plan | Build and Test after unit implementations; not a separate deployable unit |

No new business domain is introduced. The writer service identity and human Jupyter identities remain separate security principals; the shared provider is a technical runtime capability, not a shared identity service.

## Proposed decomposition

### Unit 1 — Airflow writer identity and broker

- Reintroduce the required Airflow Compose control plane and private broker service.
- Keep the writer client secret within the broker's protected Airflow boundary.
- Define initial-token issuance, run registration, renewal, expiry, and revocation contracts.
- Adapt the existing DAG factory lifecycle to create per-run auth state, pass only protected per-run data to Spark, and guarantee cleanup on all task outcomes.
- Preserve both Bundles exactly; test runtime only through `main-init_environment`.

### Unit 2 — Shared Spark runtime and identity adapters

- Establish one pinned Spark/Iceberg runtime definition and reusable token-provider implementation consumed by Airflow Spark and Jupyter single-user images.
- Upgrade Iceberg to a compatible public auth-provider extension API, with exact pin selected and validated in Functional Design.
- Implement shared expiry tracking, refresh scheduling, token replacement, and safe errors.
- Preserve separate adapters: Jupyter user broker for interactive sessions; Airflow broker and run capability for writer workloads.
- Keep human token policy and Polaris grants unchanged; do not pass the writer secret to Spark or Jupyter.

## Unit dependency and sequencing assumptions

Unit 1 establishes the writer broker API, identity contract, expiry semantics, and private TLS boundary. Unit 2 implements the Spark provider and adapters against that versioned contract. Contract tests and runtime compatibility checks run before cross-unit integration. Compose integration, Bundle validation, source checks, and main E2E happen after both units are implemented.

## Planning checklist

- [x] Map approved requirements and design components to existing component boundaries and canonical design paths.
- [x] Propose component-aligned units and dependencies.
- [x] Resolve the clarification questions below.
- [x] Review all answers for ambiguity and contradiction; no follow-up questions are needed.
- [x] Obtain user approval before generating unit artifacts.
- [x] Generate unit definitions, dependency matrix, and requirement/story mapping after plan approval.
- [x] Validate complete requirement coverage and prepare the Units Generation approval gate.

## Clarification questions

Fill every `[Answer]:` tag. If the recommendation is acceptable, enter its option letter.

### Question 1 — Unit grouping

Should implementation be organized around the two component boundaries proposed above?

A) Use Unit 1 for Airflow broker/control-plane and DAG lifecycle; Unit 2 for shared Spark runtime/provider and its two identity adapters. Integrate after both are complete (recommended).

B) Use one end-to-end unit spanning both repositories, with internal modules but a single unit gate.

X) Other; describe after the answer tag.

[Answer]:A

### Question 2 — Cross-unit interface sequencing

How should the Airflow broker and Spark provider contract be coordinated?

A) Unit 1 defines and tests a versioned request/response and capability contract first; Unit 2 implements against it, then the integrated stack is tested (recommended).

B) Develop both sides together in parallel and settle the contract during integration.

X) Other; describe after the answer tag.

[Answer]:A

### Question 3 — Repository/team ownership

What collaboration model should the unit plan assume? Current scope spans the v2 infrastructure repository and the `opensource-lakehouse` workload repository; no separate team ownership has been identified.

A) Assume one coordinated owner can make changes in both repositories, while keeping repo-specific changes and review evidence distinct (recommended).

B) Assume separate owners; require an interface handoff and approval from each repository owner before cross-repository integration.

X) Other; describe after the answer tag.

[Answer]:A

### Question 4 — Shared runtime artifact ownership

Where should the canonical shared Spark runtime definition/provider artifact be owned and built?

A) Own the reusable base/runtime and provider source in `opensource-lakehouse-infra-v2`; have both Jupyter and Airflow Spark images consume an immutable, pinned build (recommended for platform runtime consistency).

B) Own the artifact in `opensource-lakehouse`; have v2 build/pull the exact published workload runtime.

C) Keep source in v2 but build separate equivalent image variants from a shared version lock.

X) Other; describe after the answer tag.

[Answer]:A

### Question 5 — Identity boundary in the shared provider

How should the common provider be packaged relative to the identity adapters?

A) One shared provider package with separately configured Jupyter-user and Airflow-writer adapters; runtime configuration must reject missing or conflicting identity selection (recommended).

B) Publish separate Jupyter and Airflow provider packages that share a lower-level token-refresh library.

X) Other; describe after the answer tag.

[Answer]:A

## Expected generation artifacts

After this plan is answered and approved, generate:

1. `aidlc-docs/current/inception/application-design/unit-of-work.md`
2. `aidlc-docs/current/inception/application-design/unit-of-work-dependency.md`
3. `aidlc-docs/current/inception/application-design/unit-of-work-story-map.md`

Then validate unit boundaries and requirement coverage before asking for approval of the generated units.

## Answer analysis and selected plan

Recorded decisions: Q1=A, Q2=A, Q3=A, Q4=A, and Q5=A. The answers are specific and consistent. Unit 1 will define and verify the broker/API contract before Unit 2 implements the provider and adapters. One coordinated owner is assumed, with repository-specific changes and evidence kept distinct. The v2 infrastructure repository owns the canonical runtime/provider source and immutable pinned build; the workload repository consumes that build and retains the required main-branch commit/push path. The shared provider is one package with identity-specific adapters and rejects ambiguous identity configuration.

No separate business-domain unit is needed: human Jupyter identity and writer service identity stay separate principals and broker paths, while the common provider is a shared runtime component. No additional ambiguity was found in the decomposition answers.

**Planning approval:** Approved by the user on 2026-10-29. Unit artifacts are generated and ready for review; the Units Generation completion gate is still pending.
