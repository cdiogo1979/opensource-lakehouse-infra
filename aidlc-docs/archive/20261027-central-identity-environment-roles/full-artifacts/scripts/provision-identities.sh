#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

# Preserve the legacy no-argument MIT workflow. The explicit FreeIPA path is
# isolated and does not switch active authority or touch current keytabs.
if [[ "${1:-}" == "freeipa-membership" ]]; then
  if [[ $# -ne 4 ]]; then
    echo "Usage: scripts/provision-identities.sh freeipa-membership USER GROUP add|remove" >&2
    exit 2
  fi
  exec scripts/freeipa-validation.sh role-member "$2" "$3" "$4"
fi
if [[ $# -gt 0 ]]; then
  echo "Usage: scripts/provision-identities.sh [freeipa-membership USER GROUP add|remove]" >&2
  exit 2
fi

docker compose build kdc identity-provisioner
docker compose up -d --wait --wait-timeout 120 kdc
docker compose --profile identity-provisioning run --rm identity-provisioner
python3 scripts/render-metastore-config.py
docker compose restart hive-metastore
docker compose up -d --wait --wait-timeout 300 hive-metastore

echo "Identity provisioning completed; Hive Metastore now uses its named RustFS service credentials."
