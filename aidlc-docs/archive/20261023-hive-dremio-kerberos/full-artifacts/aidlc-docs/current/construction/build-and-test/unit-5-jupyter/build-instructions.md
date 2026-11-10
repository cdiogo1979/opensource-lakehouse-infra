# Build Instructions — Unit 5 JupyterHub and Per-User Spark

## Prerequisites

- Docker Engine/Desktop with Docker Compose v2 and access to the existing `iceberg-poc-net` network.
- The platform stack is already initialized. KDC principals/keytabs and matching RustFS identities for `admin`, `user_a`, and `user_b` must already exist; this build does not provision identities.
- Keep the current `.runtime` credentials and all named platform volumes. Do not run `scripts/clean.sh`, `docker compose down -v`, or volume-prune commands.
- The host's primary group is passed into matching user containers. `scripts/start.sh` detects it; for direct Compose commands export the values below.

## Build steps

Run from the project root:

```bash
export JUPYTER_CREDENTIALS_DIR="$PWD/.runtime/credentials"
export JUPYTER_EXAMPLES_DIR="$PWD/infra/jupyter/examples"
export JUPYTER_HOST_GID="$(id -g)"

./scripts/bootstrap-local.sh
chmod 640 .runtime/credentials/keytabs/admin.keytab \
  .runtime/credentials/keytabs/user_a.keytab \
  .runtime/credentials/keytabs/user_b.keytab
docker compose config --quiet
docker compose build jupyterhub
docker compose --profile jupyter-build build jupyter-singleuser-build
```

Bootstrap preserves existing credential values and changes only the six user/admin RustFS identity file modes to `0640`; the three keytabs above are also made `0640`. Parent directories remain `0700`. The writer key and keytab are not changed. Do not print credential contents.

To start only the Hub and its healthy platform dependencies, preserving already-running services:

```bash
docker compose up -d jupyterhub
docker compose ps
docker compose port jupyterhub 8000
```

Expected Hub URL: `http://127.0.0.1:8008`. The build target `jupyter-singleuser-build` is profile-only and does not start in the default service set. The Hub has no healthcheck; use `docker compose logs jupyterhub` and the browser page to confirm readiness.

## Build outputs

- `local/iceberg-jupyterhub:5.3.0`
- `local/iceberg-jupyter-singleuser:5.3.0-spark3.5.5-iceberg1.8.1`
- Named volumes `iceberg-poc-jupyterhub-data`, `iceberg-poc-jupyter-user-a-work`, `iceberg-poc-jupyter-user-b-work`, and `iceberg-poc-jupyter-admin-work`.

No image build or runtime result is claimed until the commands are run. No existing catalog, storage, Dremio, or user-work data volume should be recreated or removed.

## Troubleshooting

- **Compose reports missing credential/config files**: confirm bootstrap completed; do not delete credential files.
- **Spawn reports an unreadable identity file**: inspect only the relevant file mode and host GID. Keep parent directories `0700`; do not make the credential directory broadly readable.
- **Hub cannot reach Docker**: confirm the Docker daemon is available and the socket mount is permitted.
- **Package or base-image download fails**: check Docker's registry/package network access and retry the same build without changing pinned versions.
- **Service dependencies are unhealthy**: inspect only relevant service logs and preserve all volumes. Do not run a reset as a troubleshooting step.
