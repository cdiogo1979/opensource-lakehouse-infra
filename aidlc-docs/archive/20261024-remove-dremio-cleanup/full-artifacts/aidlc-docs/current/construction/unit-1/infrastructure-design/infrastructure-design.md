# Infrastructure Design — Dremio Removal

## Target Environment

Retain the existing single-host Docker Compose environment and its `iceberg-poc-net` network. This work removes infrastructure elements; it does not introduce or migrate to a cloud provider.

## Compose Changes

Remove from `docker-compose.yml`:

- `dremio` service, Dremio image, Java options, ports, mounts, and `dremio-data` volume declaration.
- `tpch-jdbc` profile service and its Dremio writer password secret.
- Dremio-only environment variables, including the Dremio endpoint ports and source configuration.
- Any Dremio-only image tag or JDBC driver build dependency in the TPCH loader.

Keep all other Compose services, the shared network, and retained named volumes: `object-store-data`, `metastore-db-data`, `kerberos-kdc-data`, `jupyterhub-data`, and the per-user Jupyter workspace volumes.

## Identity and Configuration Changes

- Remove Dremio principal/keytab creation and Dremio health-check authentication from the KDC scripts.
- Remove Dremio from the Kerberos provisioning identity list and extraction ACL.
- Remove `hadoop.proxyuser.dremio.*` settings from the Hive core-site template.
- Remove only Dremio password files and `.runtime/credentials/keytabs/dremio.keytab`.
- Preserve all other Kerberos principals and shared credentials.

## TPCH and Operational Script Changes

- Keep the TPCH Spark loader and its Kerberos, Hive, and RustFS configuration.
- Remove the JDBC phase, Dremio client, JDBC-driver extraction stage, and Dremio-only secrets.
- Update bootstrap, identity provisioning, startup, and cleanup scripts so they do not generate Dremio credentials, start Dremio, or remove retained data.
- Replace broad `docker compose down --volumes` cleanup behavior with explicitly scoped Dremio-only cleanup. Retained service cleanup/reset remains outside this intent.

## Runtime Cleanup Design

Runtime cleanup is a one-time, narrowly targeted operation after the source configuration is ready:

1. Confirm the Compose project/container identity and locate the Dremio container and Dremio volume by Compose labels, not by assuming an unverified volume name.
2. Stop and remove only the Dremio container. Do not stop the KDC or other retained services.
3. Inspect the candidate volume labels and attachments. Remove it only when it is uniquely identified as this project's Dremio data volume and no retained container references it. If the check is ambiguous, stop and report the candidate rather than deleting it.
4. While the existing KDC is available, delete only `dremio@<KERBEROS_REALM>` using local KDC administration. Do not reset the KDC database or remove its volume.
5. Delete only Dremio-specific password files and the Dremio keytab.
6. Verify retained containers/volumes and the non-Dremio principal set remain present.

The existing `scripts/clean.sh` currently removes all Compose volumes and multiple retained keytabs. It must be changed so its normal operation cannot violate the approved preservation boundary; it must not be used in its current form for this cleanup.

## Preservation and Safety Controls

- No `docker compose down --volumes`, whole-KDC reset, blanket credential deletion, or wildcard volume deletion.
- Do not remove Hive/PostgreSQL metadata, RustFS object data, TPCH inputs/results, JupyterHub state, or Jupyter user workspaces.
- Dremio-only removal commands must resolve their target and fail closed when the target cannot be proven unique.
- Do not print credential contents in logs or status output.

## Infrastructure Verification

Validate the rendered Compose model after edits; confirm retained service and volume names; inspect active files for Dremio operational dependencies; and verify Dremio-specific runtime state removal separately from retained data. The implementation/build stage must report which checks were actually executed.
