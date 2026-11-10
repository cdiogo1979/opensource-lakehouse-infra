#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

WRITER_KEYTAB="${ROOT_DIR}/.runtime/credentials/keytabs/write-service-account.keytab"
if [[ ! -s "${WRITER_KEYTAB}" ]]; then
  echo "ERROR: Spark requires the write-service-account keytab at ${WRITER_KEYTAB}. Run ./scripts/bootstrap-local.sh and ./scripts/provision-identities.sh before starting the stack." >&2
  exit 1
fi

export JUPYTER_CREDENTIALS_DIR="${ROOT_DIR}/.runtime/credentials"
export JUPYTER_EXAMPLES_DIR="${ROOT_DIR}/infra/jupyter/examples"
export JUPYTER_HOST_GID="$(id -g)"
export JUPYTER_HOST_UID="$(id -u)"

./scripts/bootstrap-local.sh
python3 ./scripts/validate-jupyterhub-credentials.py
docker compose build kdc create-bucket hive-schema-init hive-metastore spark jupyterhub
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
echo "JupyterHub authentication uses FreeIPA LDAPS; ensure the freeipa-validation profile and its JupyterHub reader account are ready."
echo "Hive Thrift and PostgreSQL are internal to the Compose network."
echo "Kerberos and storage authorization outcomes still require later verification."
