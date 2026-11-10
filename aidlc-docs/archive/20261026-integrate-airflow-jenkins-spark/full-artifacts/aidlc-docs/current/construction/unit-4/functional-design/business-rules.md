# Business Rules — Unit 4 Jenkins Validation

**BR-4-01 — Validation only.** Jenkins checks a checked-out revision; it does not deploy, start/stop services, build/publish platform images, change Git references, publish DAG Bundles, or operate Compose volumes.

**BR-4-02 — Isolated checkout.** Each build validates its SCM-provided revision in a Jenkins workspace. No host project directory, ignored runtime directory, secret directory, or lakehouse data volume is mounted into the build.

**BR-4-03 — Credentials stay in Jenkins configuration.** SCM credentials, when required, are stored in Jenkins credentials and referenced by the SCM job. They must not be embedded in the Jenkinsfile, URL, command arguments, or logs.

**BR-4-04 — Syntax checks do not execute project code.** Python syntax compilation and Bash parser checks may inspect source files but must not run DAGs, workload scripts, provisioning scripts, or infrastructure lifecycle commands.

**BR-4-05 — No silent empty test suite.** A build must explicitly report whether tests were discovered. An empty suite is reported as “no tests discovered,” not represented as passed test coverage.

**BR-4-06 — Failure is visible.** Missing tools, failed checks, failed discovered tests, and interrupted builds result in a failed/incomplete job result with concise actionable diagnostics.

**BR-4-07 — No socket use from the pipeline.** The Compose-approved Jenkins socket mount is retained for its existing design decision, but this validation pipeline must not use Docker CLI/API or launch containers.

**BR-4-08 — Runtime DAG registration is separate.** The production/UAT registration check is performed after Airflow starts using `scripts/verify-airflow-environment-dags.sh`; it is not a Jenkins stage and must not trigger DAGs.

**BR-4-09 — Validation claims stay bounded.** Jenkins success proves only the configured source checks passed. It does not imply Compose, service, DAG registration, Spark, Kerberos, Hive, RustFS, StarRocks, or workload integration success.
