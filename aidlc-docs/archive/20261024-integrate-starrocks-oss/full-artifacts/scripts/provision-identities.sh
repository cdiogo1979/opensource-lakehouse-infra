#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

docker compose build kdc identity-provisioner
docker compose up -d --wait --wait-timeout 120 kdc
docker compose --profile identity-provisioning run --rm identity-provisioner
python3 scripts/render-metastore-config.py
docker compose restart hive-metastore
docker compose up -d --wait --wait-timeout 300 hive-metastore

echo "Identity provisioning completed; Hive Metastore now uses its named RustFS service credentials."
