# NFR Requirements — Unit 4 Jenkins Validation

## Scope and Quality Profile

These requirements apply to the Jenkins validation-only pipeline defined by Unit 4 Functional Design. The pipeline checks out trusted source revisions, performs the specified Python and Bash syntax checks, runs maintained tests if any are later added, and reports when test discovery finds no tests. Production and UAT DAG registration remains a separate post-start operational check. Jenkins MUST NOT deploy services, build or publish platform images, mutate Git Bundle references, or use Docker lifecycle operations.

This is a single-host PoC. No availability, recovery, throughput, latency, or capacity guarantee is made. Jenkins' approved Docker socket mount remains in the Compose topology; only protected-branch or maintainer-approved revisions from trusted contributors may execute pipeline code or tests in this Jenkins context.

## Requirements

### U4-NFR-01 — Validation execution deadline

- Each validation build MUST have a maximum execution duration of 15 minutes, measured from the start of execution after an executor is assigned. Queue wait time is excluded.
- If the limit is reached, Jenkins MUST terminate the build and report it as failed due to timeout.
- Timeout reporting MUST identify the build and limit without exposing secrets.
- This is a per-build execution bound; it does not claim a maximum queue wait or end-to-end completion time.

### U4-NFR-02 — Validation build concurrency

- At most one Unit 4 validation build MAY execute at a time on this local Jenkins instance.
- Additional validation builds MUST remain queued until the active validation build completes or terminates.
- This requirement does not claim a queue-wait limit or host capacity.

### U4-NFR-03 — Build history retention

- Jenkins MUST retain no more than the latest 30 validation builds and no more than 30 days of validation build history, applying whichever limit removes history sooner.
- Retention MUST apply only to Jenkins validation build records and artifacts, if any; it MUST NOT delete source repositories, DAG Bundle references, lakehouse data, or Compose volumes.

### U4-NFR-04 — Trusted source revisions

- Jenkins MAY execute Jenkinsfile code and maintained tests only for protected-branch revisions or revisions explicitly approved by a maintainer, and only from trusted contributors.
- Arbitrary pull-request revisions MUST NOT execute in the approved Jenkins controller context while it has access to the Docker socket.
- The pipeline MUST NOT call Docker commands or otherwise use the socket. This restriction does not treat the mounted socket as a sandbox; trusted-source controls remain required because executing repository code in the controller context could access it.
- Secret values MUST NOT be committed, printed, or included in validation output.

## Verification Targets for Later Build and Test

- Confirm a validation build is terminated and marked failed at 15 minutes of execution, excluding queue time; use a controlled timeout fixture if practical.
- Start two validation builds and confirm the second remains queued while the first executes.
- Confirm retention removes history when either 30 builds or 30 days is exceeded, without affecting external source or lakehouse data.
- Inspect pipeline trigger and authorization configuration to confirm only protected-branch or maintainer-approved trusted revisions can execute; confirm arbitrary pull requests are excluded.
- Review the pipeline commands and Jenkins logs to confirm the Docker socket is unused and secret values are not exposed.
- Confirm empty test discovery is reported honestly and Python/Bash syntax checks are not described as test coverage.

## Applicability Notes

- **Availability/recovery**: Single-host local PoC; no HA, backup/restore, RTO, RPO, or host-loss recovery target.
- **Security**: The approved Docker socket mount is broad host control. Trusted-source restrictions mitigate which code can execute but do not make the socket least privilege or provide process isolation.
- **Scalability/performance**: One concurrent validation build; no queue-wait, throughput, or capacity guarantee.
- **Testing stage**: These are future verification targets. No tests were run during NFR Requirements generation.

## Traceability

| Requirement | Trace |
|---|---|
| U4-NFR-01 | US-05; FR-6; validation feedback and bounded execution |
| U4-NFR-02 | US-05; FR-6; local single-host PoC resource boundary |
| U4-NFR-03 | US-05; FR-6; bounded Jenkins validation history |
| U4-NFR-04 | US-05; FR-6; NFR-5 Docker control boundary |
