# Unit 4 NFR Design Plan — Jenkins Validation

## Approved Baseline

Unit 4 Functional Design and NFR Requirements were approved on 2026-10-26. Jenkins performs validation only: checkout trusted source revisions, Python and Bash syntax checks, and maintained tests if present, with explicit empty-test reporting. The UAT and production DAG registration check remains separate and post-start.

The accepted NFR targets are: a 15-minute build execution deadline excluding queue time; at most one validation build executing with additional builds queued; retain no more than 30 builds and 30 days, whichever limit is reached first; and allow only protected-branch or maintainer-approved revisions from trusted contributors to execute. The Jenkins Docker socket mount remains in the approved Compose topology but is not used by the pipeline. Arbitrary pull-request revisions must not execute in this controller context.

## Design Checklist

- [x] Review the approved Unit 4 Functional Design, NFR Requirements, technology decisions, Unit 3 Jenkins service configuration, and US-05/FR-6/NFR-5 traceability.
- [x] Select Jenkins-supported mechanisms for the 15-minute execution timeout, ensuring queue time is excluded and timeout yields a failed build.
- [x] Design single-build execution and queue behavior without changing the approved Jenkins topology or making a capacity claim.
- [x] Design Jenkins build-history retention at 30 builds and 30 days without affecting source repositories, Bundle references, or lakehouse volumes.
- [x] Define a fail-closed trusted-revision gate that prevents arbitrary pull-request code from executing in the socket-mounted controller context.
- [x] Preserve the validation-only command boundaries, honest empty-test reporting, and separate post-start UAT/production DAG check.
- [x] Define sanitized timeout and authorization failure reporting and identify observable verification evidence for Build and Test.
- [x] Generate NFR Design Patterns and Logical Components for Unit 4.
- [x] Validate alignment with U4-NFR-01 through U4-NFR-04 and the approved service/functional design.
- [x] Present the NFR Design artifacts for explicit approval before Unit 4 Infrastructure Design.

## Design Constraints

- Preserve the accepted 15-minute execution deadline, one-build concurrency, 30-build/30-day history limits, and trusted-source policy.
- Queue time is excluded from the execution timer; do not claim or implement a queue-wait limit.
- Trusted-source authorization must be enforced by Jenkins job/trigger configuration or another trusted control before untrusted repository pipeline code can execute. A check implemented only inside an untrusted Jenkinsfile is insufficient.
- Keep the mounted Docker socket unused by the pipeline and describe it as broad host control, not a sandbox or least-privilege boundary.
- Do not run arbitrary PR revisions on the built-in controller executor. Isolated agents or socket removal would require a separately approved topology revision.
- Keep Jenkins validation separate from Compose lifecycle, image builds/publication, deployment, Git Bundle reference mutation, and the operator-run DAG registration check.
- Do not edit Compose/Jenkins configuration, build images, start services, or run tests during NFR Design.

## Approval Gate

Generate `construction/unit-4/nfr-design/nfr-design-patterns.md` and `logical-components.md`. Explicit user approval is required before Unit 4 Infrastructure Design.

**Status**: Approved by the user on 2026-10-26. NFR Design artifacts approved; proceeding to Unit 4 Infrastructure Design planning.
