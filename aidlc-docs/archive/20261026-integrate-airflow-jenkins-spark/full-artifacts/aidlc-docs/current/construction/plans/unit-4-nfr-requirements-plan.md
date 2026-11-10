# Unit 4 NFR Requirements Plan — Jenkins Validation

## Unit and Approved Functional Baseline

This stage defines measurable quality requirements for the Jenkins validation pipeline. The approved Unit 4 Functional Design limits Jenkins to source checkout, Python and Bash syntax validation, and execution of maintained tests if a suite is later added. Jenkins does not deploy, start services, build/publish platform images, alter Bundle references, or use the Docker socket from the pipeline. The separate production/UAT DAG registration check runs only after Airflow is started.

The target and sibling repositories currently have no maintained Jenkinsfile or test suite. The functional design calls for an explicit empty-test report and a local validation image with Python 3.10, Bash, and Git. These questions cover only open, measurable NFR decisions; they do not reopen validation scope or approved Compose topology.

## NFR Assessment Checklist

- [x] Review Unit 4 Functional Design, US-05, target Jenkins Compose service, and the sibling Jenkins source.
- [x] Separate fixed validation boundaries from open measurable targets.
- [x] Ask for validation runtime, build concurrency, build history retention, and source trust requirements.
- [x] Validate answers for ambiguity or conflicts with validation-only behavior and the approved Docker socket mount.
- [x] Generate Unit 4 NFR Requirements and technology decision artifacts.
- [x] Validate traceability to US-05, FR-6, and NFR-5.
- [ ] Present the NFR Requirements for explicit approval before Unit 4 NFR Design.

## Assessment Boundaries

- **Availability/recovery**: Jenkins is a local PoC service. No uptime, HA, backup, restore, RTO, or RPO target has been approved.
- **Performance**: Ask for a validation build deadline, but make no throughput or capacity claim.
- **Scalability/resources**: No fixed CPU/memory target exists. Build concurrency must be explicit enough to avoid accidental host overload.
- **Security**: Keep secrets out of source, logs, and build arguments; keep the Compose-approved socket mount. Because Jenkins has that socket, executing untrusted Jenkinsfiles/tests could expose the Docker host. Ask which source revisions are trusted to run.
- **Maintainability/testing**: Syntax checks are not test coverage. The current empty test suite is reported explicitly; no new suite is introduced in this stage.
- **Integration**: The UAT/production DAG registration check is not part of Jenkins CI and is not a Jenkins health/performance target.

## NFR Questions

Please fill each `[Answer]:` tag. Select X and describe your preference if none of the options fits.

### Question 1 — Validation build deadline

What maximum elapsed time should a validation build have after it begins execution (excluding time queued before an executor is assigned)?

A) 15 minutes; terminate and mark the build failed if exceeded. (Recommended for syntax checks and a small local validation suite.)

B) 30 minutes; terminate and mark the build failed if exceeded.

C) No enforced deadline; retain Jenkins' normal execution behavior.

X) Other (provide a duration and timeout behavior after `[Answer]:`).

[Answer]:A

### Question 2 — Concurrent validation builds

How many Jenkins validation builds may execute concurrently on this local host?

A) One at a time; queue additional builds. (Recommended for a local PoC with no capacity guarantee.)

B) Two at a time; queue further builds.

C) Use Jenkins' configured executor count without a pipeline-specific limit.

X) Other (provide the maximum and queue behavior after `[Answer]:`).

[Answer]:A

### Question 3 — Jenkins build history retention

How much validation build history should Jenkins retain?

A) Keep at most 30 builds and 30 days of history, whichever limit is reached first. (Recommended for this local PoC.)

B) Keep at most 100 builds and 90 days of history, whichever limit is reached first.

C) Leave retention at Jenkins' configured default; do not add a pipeline retention rule.

X) Other (provide count and/or time limits after `[Answer]:`).

[Answer]:A

### Question 4 — Source trust for executing pipeline code

Which source revisions may run the Jenkinsfile and any maintained tests? Jenkins is mounted to the Docker socket by the approved Compose design, so source code executing in the Jenkins controller context could access that host-control interface even though the pipeline itself is designed not to call it.

A) Run only protected-branch or maintainer-approved revisions from trusted contributors. (Recommended; preserves the approved topology.)

B) Run arbitrary pull-request revisions only after moving their execution to an isolated agent with no Docker socket; this requires an infrastructure/design change.

C) Remove the Jenkins Docker socket mount before allowing arbitrary pull-request revisions; this revises the previously approved topology.

X) Other (describe the trusted source boundary and any isolation requirement after `[Answer]:`).

[Answer]:A

## Approval Gate

After the answers are complete and any ambiguity is resolved, generate `construction/unit-4/nfr-requirements/nfr-requirements.md` and `tech-stack-decisions.md`. Request explicit approval before Unit 4 NFR Design.

**Status**: Approved by the user on 2026-10-26. Proceeding to Unit 4 NFR Design planning.
