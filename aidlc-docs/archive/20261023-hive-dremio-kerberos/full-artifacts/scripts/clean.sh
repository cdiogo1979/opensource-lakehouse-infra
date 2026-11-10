#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

echo "This permanently deletes Compose volumes, including Hive metadata, KDC state, RustFS objects, and Dremio data."
read -r -p 'Type RESET ALL VOLUMES to continue: ' confirmation
if [[ "${confirmation}" != "RESET ALL VOLUMES" ]]; then
  echo "Reset cancelled."
  exit 1
fi

docker compose down --volumes --remove-orphans
rm -f .runtime/credentials/keytabs/hive-metastore.keytab
rm -f .runtime/credentials/keytabs/kadmin-provisioner.keytab
rm -f .runtime/credentials/keytabs/admin.keytab
rm -f .runtime/credentials/keytabs/write-service-account.keytab
rm -f .runtime/credentials/keytabs/user_a.keytab
rm -f .runtime/credentials/keytabs/user_b.keytab
rm -f .runtime/credentials/keytabs/dremio.keytab
rm -f .runtime/identity-provisioning/rustfs-ready
echo "Compose volumes were removed. Local passwords and access keys were preserved."
