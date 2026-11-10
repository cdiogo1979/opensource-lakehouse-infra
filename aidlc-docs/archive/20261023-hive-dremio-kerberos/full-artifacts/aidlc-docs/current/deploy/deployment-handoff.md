# Deployment Handoff — Hive, Kerberos, Dremio, RustFS, and JupyterHub PoC

## Handoff status

This is the approved operator handoff for the existing single-host Docker Compose PoC. The user approved continuation on 2026-10-23. No deployment command was run as part of this stage. Unit 5 Build and Test remains **partial**; outstanding checks are listed below and in `../construction/build-and-test/unit-5-jupyter/manual-verification-results.md`.

## Pull request request

**Title:** Add Hive 3.x catalog, Kerberos identities, Dremio integration, and per-user Spark notebooks

**Summary:** Replace Nessie catalog use with Hive 3.1.3 backed by PostgreSQL; add Kerberos service/user identities and the `write-service-account`; store Iceberg data in RustFS; configure the Dremio Hive source and sample Spaces/views; and add local-only JupyterHub with per-user Spark, keytab/RustFS mounts, and isolated persistent work volumes.

**Evidence recorded:** Unit 1–3 infrastructure and workload checks passed; Dremio Hive source and writer-created objects were verified; Unit 5 Compose validation and both image builds passed; Hub starts on loopback; all three configured notebook identities spawned and acquired matching Kerberos principals; a read-only admin sample Iceberg query passed. The user reports `user_b` notebook queries succeed in both databases and an access-denied result in the earlier notebook `user_a`/`databaseB` case. Separately, the user confirmed that Dremio `user_a` can successfully query `hive.databaseB.customer` after the Hive authorization settings were rendered and the Metastore restarted. That Dremio result fails the intended allow/deny matrix.

**Review before merge/acceptance:** Dremio per-user authorization is currently failing: `user_a` can query `hive.databaseB.customer` despite the Hive source using Storage Based with User Impersonation and the generated Hive authorization settings being loaded after a Metastore restart. The effective identity/storage-policy path needs diagnosis; do not treat the Dremio access matrix as enforced. The earlier notebook `user_a` denial still needs classification as Hive authorization versus RustFS/S3 denial. Unknown-label rejection, all-user mount/socket boundary review, per-user workspace isolation/persistence, and three-session capacity are also unverified. Consult the full status in `../construction/build-and-test/unit-5-jupyter/build-and-test-summary.md`.

## Ordered local startup and use

1. Confirm Docker Engine/Desktop and Docker Compose v2 are available, and allocate enough Docker memory for Dremio, Spark, Hive, RustFS, PostgreSQL, KDC, and the notebook containers.
2. From the project root, start the stack with `./scripts/start.sh`. It builds the Hub and single-user images, preserves existing credentials, and starts the Compose services. Do not use `scripts/clean.sh` or `docker compose down -v` during normal start or recovery.
3. Confirm `docker compose ps` shows the foundation services healthy/running and JupyterHub running. Inspect `docker compose logs jupyterhub` if Hub startup fails; avoid printing environment values or credential contents.
4. Open `http://127.0.0.1:8008`. The Hub uses `DummyAuthenticator`: `user_a`, `user_b`, and `admin` are test labels, and arbitrary password text is accepted. This is not real authentication; keep the Hub on localhost.
5. Open `/opt/jupyter-examples/spark-authz.py` in the user notebook. The session creates Spark with the mounted RustFS credentials, then logs Hadoop UGI into that session's own mounted keytab before its first Hive query. Query names use the configured Iceberg catalog, for example `iceberg.databaseA.customer`.
6. Verify the per-user query matrix as separate sessions: `user_a` may read `databaseA` and must be denied by Hive on `databaseB`; `user_b` may read both. Treat Kerberos, Hive connectivity, missing-table, resource, and S3/RustFS errors separately from Hive authorization.
7. Stop an individual user server from the Hub UI when finished. Its named work volume persists. To stop the whole local stack while retaining volumes and credentials, use `./scripts/stop.sh`.

## Runtime boundaries and data preservation

- JupyterHub is published only on `127.0.0.1:8008`. Its test authenticator must not be exposed to a network or treated as an identity provider.
- Each notebook container runs as non-root, receives only its own keytab and RustFS identity files read-only, joins the existing Compose network, and has its own writable named work volume. Only the Hub mounts the Docker socket.
- The existing catalog, RustFS objects, Dremio state, credentials, and notebook work volumes are persistent. Do not rotate credentials or reset volumes as routine troubleshooting.
- Airflow/Jenkins integration is out of scope for this handoff.

## Build and Test carry-forward

Unit 5 Build and Test has not been marked complete. Resolve and record these remaining items in the manual verification results before claiming full acceptance:

- Confirm the `user_a`/`databaseB` denial is a Hive authorization outcome rather than RustFS/S3 `AccessDenied`.
- Confirm unknown Hub labels are rejected.
- Inspect user and mount boundaries for `user_b` and `admin`; confirm user containers have no Docker socket.
- Confirm per-user work volume isolation and persistence across that user's server restart.
- Confirm all three sessions can remain active concurrently.

No production deployment, migration, external publication, credential rotation, or volume reset is included in this handoff.
