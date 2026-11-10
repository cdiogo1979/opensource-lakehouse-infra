# Unit 4 Code Generation Plan — Jenkins Validation

## Unit Context

- **Unit**: Unit 4 — Jenkins Validation.
- **Stories**: US-05; cross-cutting support for US-02.
- **Requirements**: FR-6, NFR-5, and U4-NFR-01 through U4-NFR-04.
- **Dependencies**: Approved Unit 4 Functional Design, NFR Requirements, NFR Design, and Infrastructure Design; Unit 1–3 code generation is complete.
- **Workspace root**: `/Users/carlosdiogo/code_repo/hive-dremio-rustfs`.
- **Existing service**: `jenkins` already exists in Compose with pinned Jenkins LTS JDK 21 image, UI port 8098, `jenkins-home`, approved Docker socket/group access, and `iceberg_net`. Preserve these boundaries.
- **Design residual**: The approved design runs builds on the built-in controller executor while the Jenkins service has Docker socket access. This is a local trusted-source PoC and is not isolated or suitable for arbitrary contributors/multi-tenant use.

This plan is the source of truth for Unit 4 Code Generation. It authorizes only the files and changes below after explicit plan approval. Do not run tests, build images, start services, or manipulate volumes during Code Generation; Build and Test owns runtime verification.

## Sequential Generation Steps

### Step 1 — Create the local Jenkins validation image

- [x] Add `infra/jenkins/Dockerfile` with the pinned existing Jenkins LTS JDK 21 base as the final stage.
- [x] Add Python 3.10 using a digest-pinned compatible Python runtime stage; provide Bash and Git, verifying runtime library compatibility at image build time. Do not change the Jenkins base, add Docker CLI/Docker-in-Docker, or install unpinned plugins/packages.
- [x] Update only the `jenkins` Compose image/build fields to use the local image and `infra/jenkins/Dockerfile` with repository-root context. Preserve service name, `8098:8080`, `jenkins-home`, `DOCKER_GID` socket group, `/var/run/docker.sock` mount, `iceberg_net`, healthcheck, and dependency behavior. Do not publish port 50000.

### Step 2 — Add validation pipeline

- [x] Add a root `Jenkinsfile` that uses the built-in executor with a top-level `agent`, starts the 15-minute execution timeout after executor assignment, converts timeout expiry to a failed build while preserving manual cancellation, uses `disableConcurrentBuilds()` queue semantics, and applies a 30-build/30-day build discarder.
- [x] Add tool preflight for Python 3.10, Bash, and Git; fail clearly when a required tool is missing.
- [x] Check out the revision selected by the configured trusted Pipeline-from-SCM job. Run Python syntax compilation and `bash -n` checks over maintained target source paths; scripts are syntax-checked but never executed.
- [x] Discover and run maintained tests only when present. Report “no tests discovered” explicitly, and do not describe syntax checks as test coverage.
- [x] Keep job result/diagnostics concise and secret-safe; do not print credentials, SCM tokens, environment dumps, or secret-bearing command output.
- [x] Ensure no pipeline stage uses Docker commands/API, Compose, runtime secrets, lakehouse data mounts, deployment, image publication, or Bundle Git ref mutation.

### Step 3 — Document trusted Jenkins job setup and boundaries

- [x] Update `README.md` with image build/use instructions and operator steps to create one Pipeline-from-SCM job from a protected trusted ref.
- [x] Document maintainer-only job configuration/trigger access, no arbitrary ref parameter or PR discovery, optional Jenkins Credentials for private Git remotes, and the procedure for maintainer-approved one-off revisions.
- [x] State clearly that a Jenkinsfile branch check cannot authorize its own revision and that trusted-source policy is enforced before repository pipeline code loads.
- [x] Document the built-in executor plus Docker socket residual risk and the limitation to trusted local PoC use; do not imply the socket is sandboxed.
- [x] Preserve the two-entry `lakehouse-main`/`lakehouse-uat` Bundle configuration and keep `scripts/verify-airflow-environment-dags.sh` as a separate post-start operator check. The later Build and Test must run it and assert production `main-init_environment` and UAT `uat-init_environment` registration; this is not a Jenkins pipeline stage.

### Step 4 — Summarize and hand off

- [x] Create `aidlc-docs/current/construction/unit-4/code/code-summary.md` listing files changed, traceability, image assumptions, trust configuration boundary, residual controller/socket risk, exclusions, and Build and Test gaps.
- [x] Update AI-DLC state, audit, and plan checklist.
- [x] No test suite was added, and no tests, syntax checks, Compose rendering, image builds, service startup/shutdown, secret reads, Docker operations, or volume operations were run during Code Generation.

## Explicitly Excluded

- Changes to Spark, Airflow DAGs, Bundle configuration, UAT/prod workload enablement, RustFS, Hive, Kerberos, catalog permissions, writer identity, or credentials.
- Adding Jenkins agents, removing or changing the Docker socket, altering the built-in executor contract, adding a Jenkins agent port, changing host port/network/volume, adding TLS, changing Jenkins authentication/users, or introducing an external CI service.
- Arbitrary pull-request execution, Jenkinsfile self-authorization, deployment, platform image publication, Bundle reference mutation, and Docker lifecycle operations from CI.
- New tests/test suites, test execution, image builds, service operations, or volume manipulation.

## Build and Test Handoff

The later Build and Test stage must:

- Render Compose and prove the Jenkins service retains its approved port, healthcheck, network, home volume, socket mount/group access, and no published port 50000.
- Build the local Jenkins image and verify Jenkins/JDK, Python 3.10, Bash, Git, runtime library compatibility, and non-root service behavior.
- Configure and inspect the Pipeline-from-SCM job so only the protected trusted ref is loaded; demonstrate arbitrary PR refs and free-form ref selection cannot execute pipeline code.
- Exercise two builds to verify queueing, the 15-minute timeout after executor assignment, and 30-build/30-day job history retention.
- Run validation on a trusted revision; confirm syntax checks and no-tests reporting; check that Docker, Compose, secrets, and lakehouse data are untouched and logs are secret-safe.
- Start Airflow per the approved deployment instructions and run `scripts/verify-airflow-environment-dags.sh`; require production `main-init_environment` and UAT `uat-init_environment` to register, while UAT/prod workloads remain disabled.
- Re-run integrated Unit 1–3 acceptance checks; no Unit 4 design check alone is evidence that those runtime flows still work.

Do not represent design review or generated pipeline source as runtime/test evidence.

## Approval Gate

Review the complete plan. Explicit approval is required before edits to Compose, Dockerfiles, Jenkins pipeline, README, or code-summary artifacts.

**Status**: Approved by user on 2026-10-26; Code Generation complete. Build and Test remains pending.
