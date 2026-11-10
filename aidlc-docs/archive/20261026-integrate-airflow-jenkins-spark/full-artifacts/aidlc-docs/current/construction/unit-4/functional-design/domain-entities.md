# Domain Entities — Unit 4 Jenkins Validation

## Validation Build

Represents one Jenkins execution for one SCM-provided source revision.

**Attributes**
- `revision`: source control revision checked out for the job.
- `workspace`: isolated Jenkins checkout and temporary cache location.
- `result`: pass, pass-with-no-tests, fail, or interrupted.
- `checks`: Python syntax, Bash syntax, and the existing automated test command when tests are present.

**Invariants**
- The revision is supplied by Jenkins SCM configuration; the job does not move or publish refs.
- The workspace does not contain runtime credentials or persistent lakehouse data.
- The job does not invoke Docker or mutate Compose services or volumes.
- A successful syntax check is never described as test coverage.

## Maintained Test Suite

Represents automated tests maintained in the repository and discoverable by the configured CI test command.

**Attributes**
- `discovered_count`: number of tests found by the test discovery step.
- `execution_result`: pass/fail/not-run.

**Invariants**
- Unit 4 does not introduce a new test suite.
- An empty discovery result is recorded explicitly.
- Any discovered maintained tests must run; failures fail the build.

## Airflow Bundle Registration Smoke Check

Represents a separate post-start verification of the Airflow deployment.

**Expected identities**
- Production: `main-init_environment` in `lakehouse-main`.
- UAT: `uat-init_environment` in `lakehouse-uat`.

**Invariants**
- The check is `scripts/verify-airflow-environment-dags.sh` and runs only after Airflow services have started.
- It verifies DAG registration only; it does not trigger DAGs, enable disabled UAT/prod configurations, or belong to Jenkins validation.
