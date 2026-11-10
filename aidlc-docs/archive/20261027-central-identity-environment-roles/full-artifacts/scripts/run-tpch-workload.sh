#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

case "${LAKEHOUSE_ENVIRONMENT:-}" in
  prod|dev|uat) ;;
  *)
    echo "ERROR: Set LAKEHOUSE_ENVIRONMENT explicitly to prod, dev, or uat." >&2
    exit 1
    ;;
esac

if [[ -z "${TPCH_DATABASES:-}" ]]; then
  echo "ERROR: Set TPCH_DATABASES to the comma-separated target database names." >&2
  exit 1
fi
export LAKEHOUSE_ENVIRONMENT TPCH_DATABASES

mkdir -p .runtime/workload/tpch-data .runtime/workload/results
chmod 700 .runtime/workload .runtime/workload/results

if [[ ! -f .runtime/identity-provisioning/rustfs-ready ]]; then
  echo "ERROR: Required Unit 2 setup marker is missing: .runtime/identity-provisioning/rustfs-ready" >&2
  exit 1
fi

for path in \
  .runtime/credentials/keytabs/write-service-account.keytab \
  .runtime/credentials/rustfs-writer-access-key \
  .runtime/credentials/rustfs-writer-secret-key; do
  if [[ ! -s "${path}" ]]; then
    echo "ERROR: Required Unit 2 setup artifact is missing: ${path}" >&2
    exit 1
  fi
done

docker compose --profile workload build tpch-generator tpch-loader

echo "Generating TPCH scale-factor-${TPCH_SCALE_FACTOR:-1} inputs..."
docker compose --profile workload run --rm tpch-generator

RUN_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
echo "Running Hive/RustFS ETL as write-service-account in ${LAKEHOUSE_ENVIRONMENT}..."
docker compose --profile workload run --rm -e "TPCH_RUN_ID=${RUN_ID}" tpch-loader

echo "TPCH Spark ETL completed; run manifest: .runtime/workload/results/${RUN_ID}.json"
