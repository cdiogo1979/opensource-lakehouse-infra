# Business Logic Model — Unit 4 Jenkins Validation

## Scope

Unit 4 defines a repository validation pipeline for the target lakehouse project. It checks source syntax and runs maintained tests when a test suite exists. It does not deploy or start services, build or publish application images, modify Git refs, or use runtime lakehouse credentials.

## Participants

- **Repository contributor** submits a change to the configured source repository.
- **Jenkins controller** loads the repository's `Jenkinsfile` and coordinates validation on its local built-in executor.
- **Validation workspace** is an isolated Jenkins job checkout. It contains the checked-out source only; runtime credentials and lakehouse data are not mounted.
- **Maintainer** reviews the job result and owns changes to the pipeline contract.

## Validation Flow

1. Jenkins checks out the revision supplied by its configured Pipeline-from-SCM job. Repository credentials, if needed, come from Jenkins credentials configuration and are not stored in the `Jenkinsfile` or logged.
2. The pipeline confirms that required tools are present and fails clearly if the validation runtime is incomplete.
3. Python source files are syntax-compiled from the supported directories. Bytecode/cache output is redirected to Jenkins temporary workspace state so source paths remain clean.
4. Maintained shell scripts under `scripts/` and `infra/` are checked with `bash -n`; scripts are not executed.
5. The pipeline discovers maintained automated tests. It runs the existing test command if tests are present. The current repository has no test suite, so it reports “no tests discovered” distinctly while keeping syntax checks as the actual validation evidence.
6. Jenkins publishes the stage result and retains ordinary Jenkins job logs according to its configured retention. It does not print secrets or modify the lakehouse.

## Runtime and Source Boundaries

- Code Generation should provide the local Jenkins validation image with Python 3.10, Bash, and Git from a pinned Jenkins base; tool versions and package source must be explicit.
- The validation job runs on the Jenkins built-in executor and requires no Docker agent, Python Docker container, Docker Pipeline plugin, or Docker socket access.
- Keep the approved Docker socket mount in Compose for the separately approved topology, but the validation pipeline does not invoke it.
- The post-start `scripts/verify-airflow-environment-dags.sh` remains an operator-run integration check. It verifies that production and UAT DAGs register after Airflow starts. Jenkins must not run it because it must not start, stop, or depend on the Compose stack.
- No runtime secret files, keytabs, RustFS credentials, Airflow metadata credentials, live service endpoints, persistent volumes, or Bundle checkout caches enter the validation workspace.

## Result Semantics

- **Pass**: checkout and all configured syntax checks pass, and any discovered maintained tests pass.
- **Pass with no tests**: checkout and syntax checks pass; the pipeline clearly reports that no automated tests were discovered.
- **Fail**: checkout, required tool preflight, syntax check, or a discovered test fails; a required command is absent; or the job is interrupted before checks finish.
- A successful validation build is not proof of Compose validity, image buildability, Airflow DAG registration, service health, or workload correctness. Those remain Build and Test checks.
