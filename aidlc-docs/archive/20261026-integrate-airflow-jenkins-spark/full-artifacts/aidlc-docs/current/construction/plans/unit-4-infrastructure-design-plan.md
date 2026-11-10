# Unit 4 Infrastructure Design Plan — Jenkins Validation

## Approved Baseline

Unit 4 Functional Design, NFR Requirements, and NFR Design are approved. Jenkins validates trusted source revisions only, using Python/Bash syntax checks and maintained tests when present; empty test discovery is reported explicitly. It does not deploy, operate Compose, build or publish platform images, mutate Git Bundle references, or run the separate post-start production/UAT DAG registration check.

Approved NFRs require a 15-minute execution timeout after executor assignment (queue time excluded), one active validation build with additional builds queued, 30-build/30-day history retention (whichever limit applies first), and a fail-closed trusted-source gate before repository pipeline code can execute. Jenkins retains its Compose-approved Docker socket mount, but validation must not use it; this socket remains broad host control. Arbitrary PR revisions must not execute on the controller.

Unit 3 already defines the Jenkins service as a pinned LTS JDK 21 image, all-interface UI port `8098:8080`, dedicated `jenkins-home` volume, approved Docker socket mount, socket group access, and `iceberg_net` Compose network. Preserve these exact service boundaries unless an incompatibility with the approved functional/NFR designs is found and raised for approval.

## Infrastructure Design Checklist

- [x] Review approved Unit 4 Functional Design, NFR Requirements, NFR Design, Unit 3 Jenkins service wiring, target Compose file, and US-05/FR-6/NFR-5 traceability.
- [x] Specify the target Jenkins validation pipeline source and SCM job configuration location, including the trusted protected-ref and maintainer-approved one-off revision policy.
- [x] Define how the trusted-source gate is enforced before Jenkins loads or executes repository-controlled pipeline code; document any limitation in the current Jenkins setup.
- [x] Specify Jenkins executor assignment and per-job serialization so concurrent validation requests queue without aborting each other.
- [x] Specify the execution timer placement so the 15-minute deadline begins after executor assignment and timeout produces a non-success result.
- [x] Define job-specific 30-build/30-day build-history retention with no effect on Git or lakehouse data.
- [x] Define the local validation runtime image/build context needed for Python 3.10, Bash, and Git, preserving the pinned Jenkins LTS JDK 21 base and explicit package sources/versions where feasible.
- [x] Map repository validation paths, test discovery/no-tests behavior, Jenkins credentials references, and sanitized result output to the approved Functional Design.
- [x] Confirm no pipeline or helper uses the Docker socket, runs shell scripts under validation, reads runtime secret files, starts Compose, or runs the DAG registration check.
- [x] Assess network, storage, security, compute, and persistence impact; preserve the existing Jenkins volume, network, socket mount, and host port without new capacity claims.
- [x] Generate Unit 4 Infrastructure Design and Deployment Architecture artifacts, record decisions deferred to Code Generation, and list Build and Test verification evidence.
- [x] Validate all design decisions against approved U4-NFR-01 through U4-NFR-04 and Unit 3 Compose constraints.
- [x] Present the Infrastructure Design artifacts for explicit approval before Unit 4 Code Generation.

## Design Boundaries

- Preserve the current Jenkins service name, pinned LTS/JDK base, `8098:8080` host binding, `jenkins-home` named volume, approved socket mount/group access, and `iceberg_net` network.
- The Functional Design calls for a local validation image with Python 3.10, Bash, and Git. Infrastructure Design must select a concrete Dockerfile/build context while retaining the approved Jenkins base; it must not silently change the service to an unrelated image.
- Trusted-ref admission must happen in Jenkins job/SCM configuration or another trusted control before the Jenkinsfile from that revision is loaded. A Jenkinsfile-only check is insufficient. If the existing Jenkins configuration cannot enforce the approved source policy without a topology/security revision, document the gap and request a decision rather than weakening the policy.
- Keep the `main` and `uat` Bundle definitions and `scripts/verify-airflow-environment-dags.sh` behavior unchanged; DAG registration verification is a separate post-start operation.
- No arbitrary PR code, deployment, service lifecycle, image publication, Git ref movement, Docker CLI/API use, runtime secret reads, or persistent lakehouse data access is permitted from validation.
- No change to the approved socket topology, Jenkins port, networks, or volumes; no TLS proxy, agent port, external CI service, or capacity guarantee.
- Do not edit Compose, Jenkins pipeline files, Dockerfiles, or runtime config; build images, start services, or run tests during this planning stage.

## Approval Gate

Review this plan before generating Unit 4 Infrastructure Design and Deployment Architecture artifacts.

**Status**: Approved by the user on 2026-10-26. Infrastructure Design artifacts approved; proceeding to Unit 4 Code Generation planning.
