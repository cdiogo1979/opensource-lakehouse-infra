#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

mkdir -p .runtime/workload/tpch-data .runtime/workload/results
chmod 700 .runtime/workload .runtime/workload/results

if [[ ! -f .runtime/identity-provisioning/rustfs-ready ]]; then
  echo "ERROR: Required Unit 2 setup marker is missing: .runtime/identity-provisioning/rustfs-ready" >&2
  exit 1
fi

for path in \
  .runtime/credentials/keytabs/write-service-account.keytab \
  .runtime/credentials/rustfs-writer-access-key \
  .runtime/credentials/rustfs-writer-secret-key \
  .runtime/credentials/dremio-writer-password; do
  if [[ ! -s "${path}" ]]; then
    echo "ERROR: Required Unit 2 setup artifact is missing: ${path}" >&2
    exit 1
  fi
done

docker compose --profile workload build tpch-generator tpch-loader

echo "Generating TPCH scale-factor-${TPCH_SCALE_FACTOR:-1} inputs..."
docker compose --profile workload run --rm tpch-generator

RUN_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
echo "Running Hive/RustFS ETL as write-service-account..."
docker compose --profile workload run --rm -e "TPCH_RUN_ID=${RUN_ID}" tpch-loader

echo "Running the separate Dremio JDBC step as write-service-account..."
docker compose --profile workload run --rm -e "TPCH_RUN_ID=${RUN_ID}" tpch-jdbc
