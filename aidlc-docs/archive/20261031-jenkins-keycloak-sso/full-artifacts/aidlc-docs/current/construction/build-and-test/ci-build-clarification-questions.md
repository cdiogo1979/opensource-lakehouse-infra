# CI Build Clarification Questions — jenkins-keycloak-sso

## Finding
The v2 Jenkins ran the full workload pipeline on `main` (#11) and `uat` (#4). Checkout, venv, compile, lint, flake8, and bandit all passed. Both builds failed on one workload-repository unit test, `test_dag_factory_reuses_spark_container_for_bundle_workloads`. Commit `00b6623` ("rename dag") renamed the DAG without updating the test. That repository is outside this intent, so the "successful workload CI build" criterion (Q11: A) is not met.

## Question 1 — How to treat the CI build criterion
A) Record it as a verification waiver for that one criterion. Jenkins executed the pipeline correctly and caught a genuine workload regression. Fix the `opensource-lakehouse` test separately, after which Jenkins rebuilds automatically on its scan (Recommended)

B) Expand scope: update the workload repository test (an edit to `opensource-lakehouse`, committed but not pushed without your instruction), then rerun the CI build here

X) Other (please describe after [Answer]: tag below)

[Answer]: A
