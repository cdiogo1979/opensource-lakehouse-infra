# NFR Design Patterns — Unit 4 Jenkins Validation

## Scope

This design translates U4-NFR-01 through U4-NFR-04 into Jenkins validation behavior. It preserves the approved Jenkins service topology and the validation-only pipeline. It does not implement or configure the controls; implementation belongs to later stages. The production/UAT DAG registration check remains a separate post-start operator action.

## 1. Executor-gated build timeout

**Pattern**: Start the 15-minute timeout only after a Jenkins executor has been assigned.

- The validation pipeline obtains its approved built-in Jenkins executor before starting its execution timer.
- Apply the pipeline timeout at the pipeline level after the top-level executor is allocated. Do not place the timeout around executor acquisition, because queue delay is explicitly excluded.
- If execution reaches 15 minutes, abort the running build and let Jenkins record a failed/aborted timeout result with the configured limit in the diagnostic.
- The timeout covers checkout and validation work performed after allocation. It does not constrain time spent waiting in the Jenkins queue.
- Do not add a global Jenkins timeout that changes unrelated jobs.

## 2. Single-build admission and FIFO queue behavior

**Pattern**: Serialize validation executions per Jenkins validation job.

- Permit one running validation build for the job. A newly requested validation build remains queued until the running build completes or terminates.
- Use Jenkins' queue and per-job concurrency behavior; do not abort the prior build or discard the queued build.
- Do not claim a queue-wait bound, throughput, or host capacity. The bound applies to execution concurrency, not other unrelated Jenkins jobs.

## 3. Bounded Jenkins build history

**Pattern**: Apply both count and age retention to validation build records.

- Retain at most 30 builds and at most 30 days, applying whichever threshold expires first.
- Apply retention only to this validation job's Jenkins build records and any job-owned artifacts. Do not remove source repository data, workspaces outside the job's Jenkins-managed retention, Git refs, Bundle revisions, lakehouse volumes, or service data.
- Let Jenkins perform its normal build-record cleanup. Cleanup must not run project scripts or Docker commands.

## 4. Trusted-revision admission before pipeline execution

**Pattern**: Select the executable pipeline definition from a trusted SCM source before loading repository-controlled pipeline code.

- Configure the Jenkins Pipeline-from-SCM job to track only the protected branch or other explicitly trusted ref. Do not expose a free-form branch/ref parameter or configure arbitrary pull-request discovery for this job.
- Permit one-off revision validation only when a Jenkins maintainer has approved the revision and the contributor is trusted; the approval must be expressed through Jenkins job/SCM configuration or an operator-controlled trigger before code execution.
- A branch check inside the Jenkinsfile is not an adequate trust gate: Jenkins has already loaded that file to run the check.
- Jenkins checks out and executes tests only from the admitted revision. Arbitrary PR revisions are rejected before any repository pipeline code or tests execute.
- The pipeline itself uses no Docker CLI/API and starts no containers. This is an operational constraint, not a sandbox: code executing on the built-in controller executor could access the mounted Docker socket. Maintain the trusted-revision restriction accordingly.
- Keep SCM credentials in Jenkins credentials; do not put secrets in parameters, source, command output, or logs.

## 5. Validation result and diagnostics

**Pattern**: Report bounded, actionable results without overstating validation evidence.

- Timeout, rejected source, missing tools, syntax failures, and failed discovered tests produce a visible non-success result with sanitized context.
- Empty test discovery is reported explicitly; syntax checks are reported as syntax checks and not as test coverage.
- A successful job means only that checkout and configured source validation succeeded. It does not prove Compose validity, DAG registration, service health, or workload correctness.
- `scripts/verify-airflow-environment-dags.sh` remains outside this pipeline and runs only after Airflow has started.

## Verification Obligations

Later Build and Test must demonstrate that queued time does not consume the 15-minute execution budget, timeout is visible as failure, one build runs while another queues, count/age retention both apply, and unauthorized PR revisions are blocked before pipeline code executes. Review Jenkins job configuration and pipeline source for source-of-truth selection, absence of arbitrary ref input, absence of Docker operations, and secret-safe output. Do not claim these controls are verified until observed in the running Jenkins service.
