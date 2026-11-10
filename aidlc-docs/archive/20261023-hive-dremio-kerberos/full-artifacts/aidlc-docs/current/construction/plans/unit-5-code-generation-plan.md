# Code Generation Plan — Unit 5 JupyterHub and Per-User Spark

## Scope and Approval

Implement the approved Unit 5 JupyterHub and isolated Spark design using the existing sibling `../jupyter-platform/` as the source baseline, adapted to this project's Hive Metastore, Kerberos, RustFS, and Compose contracts. This plan is the single source of truth for Unit 5 Code Generation. No implementation starts until the user approves the whole plan.

The generated deployment remains a local PoC. It preserves existing platform volumes, catalog data, service accounts, and all credential values, including the RustFS writer key. It does not rotate credentials, run bootstrap, build images, change permissions on disk, start/restart services, or run tests during the planning phase. Tests are not added or run in Code Generation; runtime verification remains a later stage.

## Unit Context and Story Traceability

- **Stories**: US-JH-01 (isolated Jupyter sessions for test users) and US-AUTH-03 (Spark allow/deny behavior in Jupyter).
- **Dependencies**: Units 1–3 are complete. Reuse the existing KDC realm, `user_a`, `user_b`, and `admin` keytabs, named RustFS identities, Hive Metastore, RustFS bucket/warehouse, sample databases, and `iceberg-poc-net` network.
- **Identity contract**: Only usernames `user_a`, `user_b`, and `admin` are admitted. Each maps to its matching same-named Kerberos and RustFS identity. `admin` is a JupyterHub administrator but is never substituted for test-user Spark checks.
- **Spark contract**: Local Spark uses the existing Hive Iceberg catalog and RustFS endpoint. `user_a` can read `databaseA` only; `user_b` can read both databases. RustFS access is not itself an acceptance test.
- **Persistence contract**: One Hub state volume and one stable named workspace volume per username. Preserve existing KDC/Hive/RustFS volumes and data.
- **Security contract**: Hub binds only to `127.0.0.1:8008`; DummyAuthenticator remains development-only; Docker socket is mounted only in the Hub; notebook containers run as non-root `jovyan` without privileged mode; per-user keytab and RustFS files are mounted read-only and only into the matching container; ticket cache is private and ephemeral.
- **Resource/recovery contract**: Up to three concurrent sessions, best effort, no queuing, no resource tuning, no automatic restart/retry, and manual recovery of only the affected session.
- **No Airflow/Jenkins, shared Spark service, message queue, monitoring service, or direct RustFS authorization test is added.**

## Ordered Code Generation Steps

### Step 1 — Add Hub and single-user image build mappings

- [x] Complete Step 1

- Modify `docker-compose.yml` to add the default `jupyterhub` service, a `jupyter-build` profile service for explicitly building the single-user image, loopback-only UI port `127.0.0.1:8008:8000`, Hub state/work named volumes, Docker socket only for Hub, and existing `iceberg_net` connectivity.
- Configure startup dependencies on healthy KDC, Hive Metastore, and object store without starting identity provisioning or ETL as a side effect.
- Declare `jupyterhub-data`, `jupyter-user-a-work`, `jupyter-user-b-work`, and `jupyter-admin-work` volumes; preserve all existing volumes unchanged.
- Use local image tags for Hub and single-user images; the build-only service must not start in default `docker compose up`.
- **Traceability**: US-JH-01, US-AUTH-03.

### Step 2 — Generate the Hub image and pinned dependency set

- [x] Complete Step 2

- Create `infra/jupyter/hub/Dockerfile`, `infra/jupyter/hub/requirements.txt`, and `infra/jupyter/hub/jupyterhub_config.py`.
- Retain the JupyterHub 5.3.0 base and pin DockerSpawner to `14.0.0`, with compatible direct JupyterHub Python dependencies pinned explicitly. Use upstream compatibility declarations: [DockerSpawner project](https://github.com/jupyterhub/dockerspawner) and [DockerSpawner 14.0.0 package metadata](https://pypi.org/project/dockerspawner/14.0.0/).
- Configure a fixed allowlist of `user_a`, `user_b`, and `admin`, DummyAuthenticator, and `admin` Hub role. Never accept arbitrary usernames for credential mounts.
- Configure DockerSpawner to spawn the approved single-user image on `iceberg-poc-net`, run as `jovyan`, attach the matching persistent workspace, and apply the local host primary GID as a supplementary group only for reading the individually mounted credential files.
- Map per-user host file path references without mounting or reading the RustFS credential directory in Hub and without putting credential values in Hub environment/config/logs. Attach only each username's keytab and RustFS access/secret files, each read-only.
- Configure a private tmpfs Kerberos ticket-cache location per spawned session and remove the stopped server container without removing its named work volume.
- **Traceability**: US-JH-01, US-AUTH-03, US-ID-01, US-ID-02.

### Step 3 — Generate the single-user Spark image and session startup

- [x] Complete Step 3

- Create `infra/jupyter/singleuser/Dockerfile`, `infra/jupyter/singleuser/requirements.txt`, `infra/jupyter/singleuser/spark-defaults.conf`, and `infra/jupyter/singleuser/start-session.sh`.
- Retain the current Spark 3.5.5/Iceberg 1.8.1 image baseline and install the Kerberos client package following the existing `infra/tpch-loader/Dockerfile` approach. Pin all added Python packages.
- Run the session as non-root `jovyan`; do not enable privileged mode, Docker socket access, or broad capabilities.
- Validate required mounted files without printing contents, read the matching RustFS access/secret files into the session's AWS client environment, acquire a Kerberos ticket into its private tmpfs cache, and start `jupyterhub-singleuser`. Ensure ticket cleanup occurs on process shutdown; tmpfs provides destruction when the container stops.
- Configure Spark's `iceberg` catalog against `thrift://hive-metastore:9083`, the existing Hive/Kerberos service contract, and `s3a://lake/warehouse/` via `object-store:9000`; remove all Nessie settings and shared/admin S3 credentials from the Jupyter path.
- Fail closed when a username-to-mount mapping, file read, Kerberos login, or Spark startup prerequisite is missing. Never fall back to another identity.
- **Traceability**: US-JH-01, US-AUTH-03, US-CAT-01, US-ID-01.

### Step 4 — Preserve protected host credential permissions

- [x] Complete Step 4

- Modify `scripts/bootstrap-local.sh` so only the per-user/admin RustFS access/secret files required by Jupyter are group-readable (`0640`), leaving `.runtime/` and `.runtime/credentials/` owner-only (`0700`) and leaving all credential values unchanged. Do not change the writer key's value or rotation behavior.
- Modify `infra/identity-provisioner/provision-kerberos-identities.sh` so only `admin`, `user_a`, and `user_b` keytabs used by Jupyter are group-readable (`0640`); preserve principal/keytab bytes and keep the keytab directory owner-only. Do not change the writer keytab or RustFS writer key.
- Configure the Hub to pass only the host primary GID as a supplementary group in each single-user container. The matching username receives only its own mounted files; other credentials remain unmounted.
- Preserve current Dremio/Hive/writer permission behavior. Document the permission boundary and keep secure non-root file readability as an explicit Build and Test gate.
- **Traceability**: US-ID-01, US-JH-01, US-AUTH-03.

### Step 5 — Add Spark authorization notebook example

- [x] Complete Step 5

- Create `infra/jupyter/examples/spark-authz.py` as a Jupytext-compatible notebook with direct Spark queries for `databaseA` and `databaseB` and expected outcomes for `user_a` and `user_b`.
- Do not include direct RustFS probes, credentials, ticket output, or shared-identity fallback. Mount the example directory read-only into each user container, separate from its writable work volume.
- Classify authentication, Hive connectivity, missing-object, resource, RustFS credential, and authorization outcomes distinctly.
- **Traceability**: US-AUTH-03, US-JH-01.

### Step 6 — Integrate build/start lifecycle

- [x] Complete Step 6

- Modify `scripts/start.sh` to export the absolute credential host path and host primary GID as non-secret configuration; run bootstrap; build Hub and single-user images explicitly; then perform the existing non-destructive Compose startup sequence.
- Preserve existing build/pull/readiness behavior for KDC, Hive, RustFS, Spark, and Dremio. Do not run identity provisioning or the TPCH workload automatically.
- Print the local JupyterHub URL and its DummyAuthenticator warning without printing credential values.
- **Traceability**: US-JH-01, US-DOC-01.

### Step 7 — Document operator setup and recovery

- [x] Complete Step 7

- Modify `README.md` with JupyterHub startup, local URL, allowed usernames, DummyAuthenticator limitation, image/dependency baselines, identity provisioning prerequisite, notebook examples, three-session best-effort scope, per-user workspace persistence, manual session recovery, credential protection, and Spark allow/deny expectations.
- Document how Hub and spawned containers mount only the matching identity, that the Hub has the Docker socket but no RustFS key mounts, and that host credential files remain protected by owner-only parent directories plus narrowly group-readable file modes.
- State clearly that authorization outcomes and non-root credential readability remain verification gates until Build and Test evidence exists.
- **Traceability**: US-JH-01, US-AUTH-03, US-DOC-01.

### Step 8 — Record generated implementation summary and workflow progress

- [x] Complete Step 8

- Create `aidlc-docs/current/construction/unit-5-jupyter/code/implementation-summary.md` with exact changes, identity/path mappings, startup sequence, non-destructive boundaries, permission strategy, deferred verification gates, and any compatibility decisions.
- Update this plan's checkboxes, `aidlc-docs/current/aidlc-state.md`, and `aidlc-docs/current/audit.md`.
- Do not add or execute tests in this stage. Do not build images, run bootstrap, start/restart services, query data, modify persistent state, or rotate credentials.
- **Traceability**: US-JH-01, US-AUTH-03, US-DOC-01.

## Exact File Changes

### Modify

- `docker-compose.yml`
- `scripts/start.sh`
- `scripts/bootstrap-local.sh`
- `infra/identity-provisioner/provision-kerberos-identities.sh`
- `README.md`
- `aidlc-docs/current/aidlc-state.md`
- `aidlc-docs/current/audit.md`

### Create

- `infra/jupyter/hub/Dockerfile`
- `infra/jupyter/hub/requirements.txt`
- `infra/jupyter/hub/jupyterhub_config.py`
- `infra/jupyter/singleuser/Dockerfile`
- `infra/jupyter/singleuser/requirements.txt`
- `infra/jupyter/singleuser/spark-defaults.conf`
- `infra/jupyter/singleuser/start-session.sh`
- `infra/jupyter/examples/spark-authz.py`
- `aidlc-docs/current/construction/unit-5-jupyter/code/implementation-summary.md`

No other source files, sibling project files, credentials, or runtime data are in scope.

## Stop Conditions and Preservation

- If the existing credential file modes/ownership or Docker host group mapping cannot allow `jovyan` to read only its individually mounted files without exposing other host files, stop and request review of the smallest secure alternative; do not make the credential directory broadly readable.
- If `admin`, `user_a`, or `user_b` identity files are absent, report the prerequisite; do not provision or rotate identities as part of Hub startup.
- If JupyterHub/Spark dependency compatibility requires changing approved image baselines, stop and request review rather than silently upgrading.
- If Hive/RustFS cannot enforce the approved user matrix, preserve data/credentials and report the gate; never use admin or writer as a fallback.
- Keep all existing named volumes, Hive databases/tables, Dremio objects, RustFS objects, and credential values unchanged. In particular, do not rotate or modify the RustFS writer key.

## Approval Status

**Plan status: Approved by user on 2026-10-23; implementation in progress.**
