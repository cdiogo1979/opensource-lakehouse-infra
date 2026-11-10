#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

export JUPYTER_CREDENTIALS_DIR="${ROOT_DIR}/.runtime/credentials"
export JUPYTER_EXAMPLES_DIR="${ROOT_DIR}/infra/jupyter/examples"
export JUPYTER_HOST_GID="$(id -g)"

./scripts/bootstrap-local.sh
docker compose build kdc create-bucket hive-schema-init hive-metastore jupyterhub
docker compose --profile jupyter-build build jupyter-singleuser-build
docker compose pull --ignore-buildable
docker compose up -d
docker compose wait hive-schema-init create-bucket
docker compose up -d --wait --wait-timeout 300

echo
echo "Foundation services are ready."
echo "RustFS:       http://$(docker compose port object-store 9001)"
echo "Spark UI:     http://$(docker compose port spark 8080)"
echo "JupyterHub:  http://127.0.0.1:${JUPYTERHUB_PORT:-8008}"
echo "WARNING: JupyterHub uses DummyAuthenticator; keep it on localhost for this PoC."
echo "Hive Thrift and PostgreSQL are internal to the Compose network."
echo "Kerberos and storage authorization outcomes still require later verification."
