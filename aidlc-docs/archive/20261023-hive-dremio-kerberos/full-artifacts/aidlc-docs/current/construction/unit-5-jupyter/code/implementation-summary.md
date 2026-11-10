# Unit 5 Code Generation — Implementation Summary

## Generated Scope

The approved Unit 5 plan is implemented in the target project. The existing Hive Metastore, Kerberos realm, RustFS endpoint, and Spark 3.5.5/Iceberg 1.8.1 catalog baseline are reused. The Jupyter path has no Nessie configuration, shared/admin credential fallback, Airflow/Jenkins integration, or direct RustFS authorization probe.

### Modified files

- `docker-compose.yml` — default local-only JupyterHub service, explicit single-user build-profile target, Hub state and per-user workspace volumes, and startup dependency mapping.
- `scripts/start.sh` — exports host credential/example paths and primary GID, explicitly builds both images, and prints the local Hub URL and DummyAuthenticator warning.
- `scripts/bootstrap-local.sh` — sets only the admin, user_a, and user_b RustFS access/secret files to mode `0640`; parent runtime/credential directories remain mode `0700` and values are preserved.
- `infra/identity-provisioner/provision-kerberos-identities.sh` — sets only the admin, user_a, user_b, and existing Dremio keytabs to mode `0640`; writer and other keytabs remain mode `0600`.
- `README.md` — documents startup, local-only DummyAuthenticator, identity prerequisites, per-user boundaries, example queries, recovery, and remaining verification gates.

### Created files

- `infra/jupyter/hub/Dockerfile`
- `infra/jupyter/hub/requirements.txt`
- `infra/jupyter/hub/jupyterhub_config.py`
- `infra/jupyter/singleuser/Dockerfile`
- `infra/jupyter/singleuser/requirements.txt`
- `infra/jupyter/singleuser/spark-defaults.conf`
- `infra/jupyter/singleuser/start-session.sh`
- `infra/jupyter/examples/spark-authz.py`

## Identity and Storage Mapping

| Hub label | Kerberos principal/keytab | RustFS files | Persistent workspace |
|---|---|---|---|
| `user_a` | `user_a@LAKEHOUSE.LOCAL`, `keytabs/user_a.keytab` | `rustfs-user-a-access-key`, `rustfs-user-a-secret-key` | `iceberg-poc-jupyter-user-a-work` |
| `user_b` | `user_b@LAKEHOUSE.LOCAL`, `keytabs/user_b.keytab` | `rustfs-user-b-access-key`, `rustfs-user-b-secret-key` | `iceberg-poc-jupyter-user-b-work` |
| `admin` | `admin@LAKEHOUSE.LOCAL`, `keytabs/admin.keytab` | `rustfs-admin-access-key`, `rustfs-admin-secret-key` | `iceberg-poc-jupyter-admin-work` |

The Hub allowlist contains only these three labels. DockerSpawner mounts each identity's three individual credential files read-only and passes the host primary GID as a supplementary group to the corresponding non-root `jovyan` container. The Hub itself receives only host path references and the Docker socket; it does not inspect or mount credential files. The single-user startup checks readability, reads the matching RustFS files without printing them, and obtains a Kerberos ticket in a private tmpfs cache. The Spark example supplies the matching RustFS identity to Iceberg's catalog configuration and enables Spark's credential redaction. The Hub UI binds to `127.0.0.1:8008`, and the user containers join `iceberg-poc-net` without host-published ports or Docker socket access.

## Startup and Operator Behavior

Run `./scripts/start.sh` from this project. It bootstraps local files without rotating their values, builds the Hub and single-user images, then preserves the existing platform startup sequence. The single-user build target is excluded from default Compose startup and is built explicitly under the `jupyter-build` profile. Hub startup does not provision identities or run ETL.

Open <http://127.0.0.1:8008> and use one of the configured labels. DummyAuthenticator does not verify human identity, so this remains a localhost PoC. `infra/jupyter/examples/spark-authz.py` provides the direct Spark examples: `user_a` should allow `databaseA` and deny `databaseB`; `user_b` should allow both. Only an identifiable authorization decision counts as a deny. Session/server cleanup preserves the matching user's named workspace volume.

## Preservation and Verification Status

- No credential values were read, printed, changed, or rotated during generation. In particular, the RustFS writer key and writer keytab behavior were left unchanged.
- No Docker image was built, bootstrap command run, service started/restarted, data queried, or test executed in this stage.
- Build and Test must still establish that the pinned Python dependencies build together, JupyterHub can spawn sessions, non-root `jovyan` can read only its mounted identity files, Kerberos authenticates each matching principal to Hive, RustFS access works with each user credential, per-user work volumes remain separate/persistent, and the Spark database matrix is enforced.
- No verification result is claimed. The database authorization and effective-user behavior remain feasibility gates; a failure must not trigger admin/writer fallback or broader policy.

## Extension Applicability

- Security Baseline: disabled by the approved project setting; the approved credential isolation and local-only requirements were retained.
- Property-Based Testing: partial setting; no tests were added or run, as required by the approved Code Generation plan. Revisit in Build and Test only if the approved verification plan calls for it.
- Resiliency Baseline: disabled by the approved project setting; operator-led recovery and persistence follow the approved Unit 5 NFRs.
