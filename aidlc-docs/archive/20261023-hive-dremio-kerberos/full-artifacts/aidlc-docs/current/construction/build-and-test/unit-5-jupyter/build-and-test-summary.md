# Build and Test Summary — Unit 5 JupyterHub and Per-User Spark

## Status

**IN PROGRESS — builds and Hub startup passed; per-session acceptance remains pending.** Existing platform data and credential values were preserved.

## Build

- Compose parse: **PASS** — `docker compose config --quiet` exited successfully.
- JupyterHub image (`local/iceberg-jupyterhub:5.3.0`): **PASS** — built successfully.
- Single-user image (`local/iceberg-jupyter-singleuser:5.3.0-spark3.5.5-iceberg1.8.1`): **PASS** — built successfully with the profile-only target.
- Hub startup: **PASS** — `iceberg-poc-jupyterhub` is running; startup logs show JupyterHub 5.3.0 and the configured `admin`, `user_a`, and `user_b` labels.
- Loopback binding: **PASS** — Docker publishes `127.0.0.1:8008`; host request returned HTTP 302 to the login flow.
- Credential readability preparation: **PASS** — the three user keytabs and six matching RustFS files are `0640`; `.runtime`, `.runtime/credentials`, and the keytabs directory remain `0700`. No values were read or changed. Writer and Hive credential values were not modified.
- DockerSpawner correction: the first spawn attempt exposed that `group_add` was passed to Docker's container-create API instead of the host-config API. Moved it to `extra_host_config`, rebuilt the Hub image, and recreated only the Hub container.

## Verification Categories

- Unit tests: N/A; no Unit 5 unit-test harness or tests were generated in the approved plan.
- Integration: **PARTIAL** — after the spawn fix, local login/spawn smoke checks passed for `user_a`, `user_b`, and `admin`; all three ran as `10001:10001`, read their own mounted keytab/RustFS files, and acquired the matching Kerberos principal. The `user_a` container's supplementary group and read-only mount flags were inspected. A read-only Spark query of `iceberg.databaseA.customer` passed in the `admin` container after explicitly logging Hadoop UGI into its mounted keytab. The user reports that `user_b` read queries succeeded in both databases and that the expected `user_a` denial occurred for `databaseB`; the denial's exception category remains unconfirmed. Unknown-label rejection, complete RustFS-backed query verification, workspace isolation/persistence, and three simultaneous sessions remain pending; see `manual-verification-results.md`.
- Performance: N/A; no numeric performance objective was approved. Three-session capacity is checked as integration.
- Security: **PARTIAL** — loopback-only port and credential parent/file modes were verified. The `user_a` spawned-container user, supplementary group, read-only identity/example mounts, and writable work mount were inspected. Unknown-label rejection, the corresponding detailed mount/socket inspection for all users, and any vulnerability scan remain pending; no scanner is configured.
- Python code quality: N/A; this repository has no `cicd/Jenkinsfile`, `requirements-dev.txt`, or `scripts/code_quality.sh` quality pipeline.

## Open Gates

Verify unknown-label rejection; Kerberos-authenticated Hive query access; RustFS access for Iceberg queries; per-user work-volume separation/persistence; three concurrent sessions; and the expected Spark `databaseA`/`databaseB` matrix. Record remaining results in `manual-verification-results.md`. No result is considered passed until evidence is recorded. A failure must not trigger admin/writer fallback, data reset, or credential rotation.
