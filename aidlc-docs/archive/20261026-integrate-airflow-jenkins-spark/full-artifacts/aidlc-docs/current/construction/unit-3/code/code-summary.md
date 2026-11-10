# Unit 3 Code Summary — Airflow and Jenkins Compose Integration

## Generated Files

- `docker-compose.yml` — adds a dedicated Airflow PostgreSQL database/volume, Airflow 3.3.2 initializer/API/scheduler/DAG processor/triggerer, Jenkins LTS and its home volume; preserves the existing service/network/volume declarations and JupyterHub socket mount.
- `infra/airflow/Dockerfile` — builds one shared Airflow controller image from the pinned official Airflow 3.3.2 Python 3.10 image digest and installs Git, Docker, FAB, and PostgreSQL providers under the matching official constraints.
- `infra/airflow/requirements.txt` — declares the required Airflow providers, resolved through the pinned Airflow constraints.
- `infra/airflow/airflow-entrypoint.sh` — validates deployment-supplied path/Bundle configuration and prepares a scheduler-only temporary project path view with empty mode-`0600` credential placeholders.
- `infra/airflow/validate-bundle-config.py` — rejects missing/relative host-path inputs, embedded URL credentials, malformed Bundle JSON, or any Bundle list other than the maintained `lakehouse-main`/`lakehouse-uat` pair and their expected refs/connection/sparse dirs.
- `scripts/verify-airflow-environment-dags.sh` — waits for and asserts production DAG `main-init_environment` from `lakehouse-main` and UAT DAG `uat-init_environment` from `lakehouse-uat`; checks registration only and never triggers either DAG.
- `infra/airflow/airflow-secret-command.py` — renders the isolated Airflow PostgreSQL SQLAlchemy URL from a protected secret file for Airflow's supported `_CMD` configuration.
- `infra/airflow/bootstrap-airflow-admin.py` — calls the supported Airflow user CLI in-process, keeps the password out of the OS process argument vector, suppresses CLI/log output, and creates the configured administrator only when absent.
- `scripts/provision-airflow-secrets.sh` — creates missing Airflow-only files securely with `0600` permissions, preserves existing values, and does not print secret contents.
- `README.md` — documents startup inputs, ports/exposure, path mappings, Docker socket boundaries, health interpretation, secrets, volumes, and Bundle retention behavior.

## Traceability

| Requirement | Implementation |
|---|---|
| Airflow Git Bundle controller and isolated metadata | Dedicated Airflow image/services and PostgreSQL volume; the maintained `lakehouse-main` and `lakehouse-uat` bundle list is validated. |
| Per-run Spark execution integration | Scheduler Docker socket, host-visible project/bundle paths, existing service network, and scheduler path view; real writer files are mounted by Docker Engine directly into Spark run containers. |
| File-backed Airflow secret handling | Protected helper files and `_CMD` settings for DB, Fernet, API, and JWT values; admin password is available only to the initializer. |
| Jenkins validation service | Pinned official Jenkins LTS image, persistent home, internal network, UI port 8098, and approved Docker socket. Pipeline content remains Unit 4. |
| Health and persistence | Dedicated database health check, API `/api/v2/version` check with the approved timing, independent Jenkins HTTP check, and isolated named volumes. |
| Preserve existing lakehouse state | Existing ports, services, profiles, credentials, network, volumes, and JupyterHub socket mount remain in Compose. No volume operations were performed. |

## Boundaries and Build and Test Gaps

- No existing Spark, DAG factory, writer identity, keytab, RustFS credential, Hive, StarRocks, or lakehouse volume was changed.
- No secret-generation helper was run. No secret contents were inspected.
- No tests or verification scripts were run, Compose render was not run, images were not built, and services were not started or stopped during Code Generation. The DAG registration verification script must be run during Build and Test.
- Airflow image/provider installation, Compose interpolation, secret UID/GID access, admin bootstrap, host/Docker path identity, Jenkins startup, Git authentication, health behavior, and persistent-volume behavior are unverified until Build and Test.
- Bundle provider checkouts remain writable to the DAG processor and scheduler; Spark driver mounts are read-only. Automatic Bundle pruning remains disabled to protect active run revisions.
- Both UI ports bind all host interfaces using HTTP without TLS termination, per the approved deployment decision.
- The Docker socket remains mounted into the pre-existing JupyterHub, and is newly mounted only into Airflow scheduler and Jenkins among the Unit 3 services.
- Unit 4 still owns the validation-only Jenkins pipeline configuration and its CI behavior.

## Image References

- Airflow base: `apache/airflow:3.3.2-python3.10@sha256:db151dc175a22504ba8729ec38dd3964326935dfa6c4c2d6480ebd14d33b3b29`.
- Jenkins: `jenkins/jenkins:lts-jdk21@sha256:a660310e39ade10631f774bacd5219de767dfd08947ea5c32a739b5e5bb382c1`.
- PostgreSQL reuses the target's existing immutable PostgreSQL 16 image reference.
