# Unit 3 Code Generation Planning — Extension Clarifications

This file records the user's Property-Based Testing, Resiliency, and CI-provider choices. Full extension enforcement applies unless explicitly scoped N/A by the recorded answers. The existing requirements scope this work to a local Compose profile and explicitly declined only the broader Security Baseline; required token and authorization safeguards remain in scope.

## Question 1 — Property-Based Testing extension

Should property-based testing rules be enforced for this unit's role matrix, resource-path, and runtime-configuration invariants?

A) Full enforcement — add Hypothesis-based properties for valid role/environment/operation combinations, approved table paths, and credential/cache invariants (Recommended for these enumerable business invariants).

B) Partial enforcement — apply property-based tests only to pure functions and serialization/configuration invariants.

C) No — skip the Property-Based Testing extension; retain the focused example-based tests already planned.

X) Other (describe after `[Answer]:`).

[Answer]:A

## Recorded resolutions

- **Q1 — PBT:** Full enforcement. Functional Design now lists testable properties in `aidlc-docs/current/construction/unit-3/functional-design/business-logic-model.md`; Code Generation plans Hypothesis strategies, oracle/invariant properties, shrinking, seed replay, and complementary example tests.
- **Q2 — Resiliency scope:** Apply local dependency timeouts, bounded pools, health checks, and failure containment. Production HA, multi-region, auto-scaling, and DR controls are N/A for this local profile.
- **Q3 — Resiliency testing:** Defer execution to a separately scheduled validation activity. Capture failure scenarios and owner in Build and Test / Deploy Handoff.
- **Q4 — Change and incident process:** Formal production change management and incident response are N/A for this local proof-of-concept; retain AI-DLC review gates.
- **Q5 — CI provider:** Jenkins. Add a root Jenkins pipeline test stage that runs the Python suite with Hypothesis and logs a reproducible seed.

## Question 5 — CI provider for required PBT integration

The project currently has no CI workflow. Full PBT enforcement requires the PBT suite to run in CI and report a replayable seed on failure. Which CI integration should Code Generation include?

A) Add a GitHub Actions workflow for the focused Python test suite, including Hypothesis seed reporting (Recommended if this repository is hosted on GitHub).

B) Add a Jenkins pipeline stage for the focused Python test suite, including Hypothesis seed reporting (provide the Jenkins endpoint or repository pipeline convention if not already in this project).

C) Use another existing CI provider; specify its name and the workflow convention to follow.

D) No CI provider is available now; accept a documented PBT-08 gap and defer CI integration.

X) Other (describe after `[Answer]:`).

[Answer]:B

## Question 2 — Resiliency extension scope

How should the baseline resiliency rules apply to this explicitly local, single-host development profile?

A) Apply relevant dependency timeout, pool, health, and failure-containment rules; mark production-only HA, multi-region, auto-scaling, and DR controls N/A for this local profile (Recommended; keeps scope aligned to the approved local deployment).

B) Expand the intent to production readiness, including availability/recovery targets, HA/DR, CI/CD, rollback, monitoring, and incident operations. This changes the approved scope and requires additional design.

X) Other (describe after `[Answer]:`).

[Answer]:A

## Question 3 — Resiliency test approach

How should failure/recovery testing be handled for this local profile?

A) Defer execution to a separately scheduled validation activity; document relevant failure scenarios and owners in later Build and Test / Deploy Handoff artifacts (Recommended; this intent does not introduce production DR or chaos operations).

B) Use an existing DR, game-day, or chaos-testing practice (provide its reference after `[Answer]:`).

C) Propose a recurring DR/chaos testing schedule and experiment plan for adoption.

X) Other (describe after `[Answer]:`).

[Answer]:A

## Question 4 — Change-management and incident-response applicability

Which process boundary should this local, non-production intent use?

A) Treat formal change management and production incident response as N/A for this local proof-of-concept; document the non-production rationale and keep changes behind the AI-DLC review gates (Recommended).

B) Use an existing organizational change-management and incident-response process (provide the names/references after `[Answer]:`).

C) Propose lightweight change and incident procedures for adoption, expanding the operational scope of this intent.

X) Other (describe after `[Answer]:`).

[Answer]:A
