#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [[ ! -s .runtime/credentials/dremio-admin-password || ! -s .runtime/credentials/dremio-writer-password ]]; then
  echo "ERROR: Run scripts/bootstrap-local.sh and complete Dremio local account setup first." >&2
  exit 1
fi

docker compose build kdc identity-provisioner
docker compose up -d --wait --wait-timeout 120 kdc
docker compose --profile identity-provisioning run --rm identity-provisioner
python3 scripts/render-metastore-config.py
docker compose restart hive-metastore
docker compose up -d --wait --wait-timeout 300 hive-metastore
docker compose up -d --force-recreate --wait --wait-timeout 180 dremio

echo "Identity provisioning completed; Hive Metastore now uses its named RustFS service credentials."
