# Unit 4 Build and Test Summary — Jenkins Validation and Airflow DAG Registration

**Status: Partial.** Local image, configuration, service health, DAG registration, and user-reported UAT/production DAG executions passed. Jenkins Pipeline-from-SCM behavior and platform reliability checks remain unverified.

## Build and configuration results

- `docker compose config -q`: passed with the documented host path, UID, and Docker socket group values.
- Jenkins validation image: built successfully from its pinned Jenkins and Python bases. Build-time checks confirmed Python 3.10, required runtime imports, Bash, and Git.
- Jenkins image runtime: passed in a disposable container as `uid=1000(jenkins)`; Python 3.10.22, Bash, and Git were available.
- Airflow image: built after correcting its Dockerfile to install providers as the `airflow` user, as required by the pinned Airflow base.
- Airflow metadata initialization: passed after changing the file-backed SQLAlchemy URL helper to write the URL without a trailing newline.
- Compose startup: Airflow PostgreSQL and API server are healthy; scheduler, DAG processor, triggerer, and Jenkins are running; Jenkins is healthy. Existing Hive, KDC, RustFS, Spark, JupyterHub, and StarRocks containers were not recreated.
- Jenkins ports: 8098 is host-published; Docker inspection confirms 50000/tcp has no host binding.

Airflow's five dedicated secret files were created using `scripts/provision-airflow-secrets.sh`; values were not displayed. The `lakehouse_git` Airflow connection was created without credentials because the configured public repository cloned anonymously. Compose initialized only the new Airflow metadata and Jenkins home volumes; no existing lakehouse data volume was reset or removed.

## Validation results

- In a disposable Jenkins image container, mounted read-only, Python syntax compilation passed for 21 files; Bash syntax checks passed; no Python tests were discovered.
- The Jenkinsfile's local validation commands were repeated on 2026-10-27: Python syntax compilation passed for 21 files, `bash -n` passed for shell scripts under `scripts/` and `infra/`, and no `tests/` directory/test files were found.
- Static inspection confirmed the Jenkinsfile includes trusted SCM checkout, a 15-minute execution timeout, serialized builds, a 30-build/30-day discard policy, workspace cleanup, and no Docker command use. These source checks do not prove Jenkins executes the Declarative Pipeline as intended.
- `scripts/verify-airflow-environment-dags.sh`: passed. It verified production `main-init_environment` from `lakehouse-main` and UAT `uat-init_environment` from `lakehouse-uat`.
- The user reports that the production DAG completed successfully and that the UAT DAG also executed correctly after recreating the UAT branch from `main`. Treat those as successful runtime checks. No changes were made to the `opensource-lakehouse` source as part of the current verification follow-up.
- Jenkins plugins are now installed in the new project's Jenkins home and expanded in the running container: `workflow-aggregator` 608.v67378e9d3db_1, `pipeline-model-definition` 2.2293.v6e7193cec599, `git` 5.11.0, `git-client` 6.6.1, and required Workflow components. No Jenkins jobs are configured yet. The unauthenticated Linter request was rejected with HTTP 403 because the initial-admin password file has been removed after setup and anonymous access cannot obtain a crumb. No Jenkins validation build was run.

### Jenkins pipeline run evidence — 2026-10-27

- The configured multibranch job `opensource-lakehouse-dp/opensource-lakehouse-ci` was inspected read-only inside the running Jenkins container.
- Latest `main` build **#10** (revision `8f7ca28d48a0d3d1dc955f23a632d84be3bbf657`, 10:45 UTC) completed successfully. Its console log shows the parallel code-analysis stages, Bandit reporting no issues, and **48 unit tests passed**. This confirms Jenkins executed the checked-in pipeline on `main`.
- Latest `uat` build **#2** (revision `eaac4063a8b4a816ee9d512090aa492d79cf0a10`, 10:14 UTC) failed in `Unit tests`: `python3 -m pytest -q` returned `/usr/local/bin/python3: No module named pytest`. Its log has no dependency-install stage. The current checked-out `main` Jenkinsfile creates `.venv`, installs `requirements-dev.txt`, and invokes `.venv/bin/python`; therefore the UAT failure is consistent with that run checking out an older pipeline revision. No UAT build after the reported branch recreation was present in Jenkins at inspection time.
- The local `opensource-lakehouse` clone has `main` at `8f7ca28` and no local `uat` branch, so it cannot independently establish the current remote UAT revision. No source files were changed.
- The reported pipeline error is diagnosed, but UAT pipeline verification remains open until Jenkins builds the recreated/current UAT branch and completes successfully. Main passing does not prove that UAT is current.

## Remaining verification

- Add the installed plugin versions to the Jenkins image definition so the plugin set survives a fresh Jenkins home, while preserving the separate home volume. The target project's Pipeline-from-SCM job is now configured and has executed; durable plugin installation in a fresh Jenkins home remains unverified.
- Jenkins main execution is verified by build #10. A successful UAT execution is still needed after the branch recreation because UAT build #2 failed using an older pipeline revision. Pipeline Linter, trusted-ref admission, queue behavior, timeout failure behavior, 30-build/30-day retention, and workspace cleanup are not established by those runs.
- Repeat or capture evidence for platform-specific Unit 1–3 checks not demonstrated by the successful UAT/production DAG runs, including worker renewal/recovery, per-run cleanup/decommission behavior, and concurrent-run limits.

Jenkins and Airflow services are left running for operator review. Do not claim full intent verification or deploy readiness from this partial result.

The live Airflow import-error and DAG-list commands were not rerun during the latest follow-up because permission to inspect the running Compose environment was declined. This does not override the user's report that both environment DAGs executed successfully.

Jenkins checks on 2026-10-27 remain static/local only. Pipeline/Workflow/Git plugins are installed in the current Jenkins home, but no job is configured; anonymous Linter access is blocked by Jenkins CSRF protection. Jenkins job execution and its runtime queue, timeout, retention, trust, and cleanup behavior remain unverified. Plugin installation is currently in Jenkins home rather than the Docker image definition.

## Verification waiver

On 2026-10-27, the user accepted the verification gaps listed above and directed the workflow to proceed. The waiver covers Jenkins Pipeline Linter and trusted Pipeline-from-SCM execution, reproducible plugin installation in a fresh Jenkins home, Jenkins runtime queue/timeout/retention behavior, and Unit 1–3 worker renewal/recovery, per-run cleanup/decommission, and concurrency checks. These items remain **unverified**, not passed. The user-reported successful UAT and production DAG executions remain recorded as separate evidence. The AI-DLC lifecycle is `VERIFICATION_WAIVED`; closure still requires review and separate approval of the archive/cleanup dry-run.

## User-reported follow-up

After the RustFS `write-service-account` policy was widened to the complete `lake` bucket, the user reported on 2026-10-26 that all tests were fine and approved continuing to the Deploy handoff. The provisioner independently confirmed that the exact writer policy was installed and that the existing writer credentials can list the complete bucket. No secret rotation was performed. On 2026-10-27, the user further confirmed successful production and UAT DAG runs. Build and Test remains partial only for Jenkins trusted Pipeline-from-SCM validation and the platform reliability checks listed above; no verification waiver has been recorded.
