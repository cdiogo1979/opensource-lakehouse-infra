#!/usr/bin/env bash
set -euo pipefail

RESULTS_DIR="${TPCH_RESULTS_DIR:-/run/results}"
RUN_ID="${TPCH_RUN_ID:?TPCH_RUN_ID is required}"
MANIFEST="${RESULTS_DIR}/${RUN_ID}.json"

if [[ ! -s "${MANIFEST}" ]]; then
  echo "ERROR: ETL run manifest is unavailable." >&2
  exit 1
fi
if [[ ! -s /run/secrets/dremio-writer-password ]]; then
  echo "ERROR: Dremio writer credential is unavailable." >&2
  exit 1
fi

/opt/spark/bin/spark-submit \
  --master 'local[1]' \
  --conf spark.driver.extraJavaOptions="${SPARK_SUBMIT_OPTS:-}" \
  /infra/tpch-loader/dremio_jdbc.py
