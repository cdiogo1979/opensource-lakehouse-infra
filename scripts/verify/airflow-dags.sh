#!/usr/bin/env bash
set -euo pipefail

# Verify that Airflow has parsed every data product's production and UAT Bundle
# (<product>-main and <product>-uat, from data-products/*.yaml): each must supply
# at least one DAG. DAG IDs that do not start with their bundle name are reported,
# because the token broker refuses writer tokens to them.
cd "$(dirname "$0")/../.."
timeout_seconds="${AIRFLOW_DAG_VERIFY_TIMEOUT_SECONDS:-300}"
AIRFLOW_COMPOSE=(docker compose -f compose.core.yml -f compose.airflow.yml --profile airflow)
if ! [[ "$timeout_seconds" =~ ^[1-9][0-9]*$ ]]; then
  echo "AIRFLOW_DAG_VERIFY_TIMEOUT_SECONDS must be a positive integer" >&2
  exit 2
fi

LAKEHOUSE_EXPECTED_BUNDLES="$(python3 scripts/setup/stage-airflow-writers.py --list)"
export LAKEHOUSE_EXPECTED_BUNDLES
if [[ -z "$LAKEHOUSE_EXPECTED_BUNDLES" ]]; then
  echo "No data product has a repo; there are no Airflow Bundles to verify."
  exit 0
fi

deadline=$((SECONDS + timeout_seconds))
while (( SECONDS < deadline )); do
  if dag_json="$("${AIRFLOW_COMPOSE[@]}" exec -T airflow-dag-processor airflow dags list --output json 2>/dev/null || true)" \
    && printf '%s' "$dag_json" | python3 -c '
import json
import os
import sys

try:
    payload = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(1)

if isinstance(payload, dict):
    rows = payload.get("dags", payload.get("data", []))
else:
    rows = payload
if not isinstance(rows, list):
    sys.exit(1)

expected = os.environ["LAKEHOUSE_EXPECTED_BUNDLES"].split()
dags = {}
for row in rows:
    if isinstance(row, dict):
        dags.setdefault(row.get("bundle_name"), []).append(str(row.get("dag_id")))
missing = [bundle for bundle in expected if not dags.get(bundle)]
if missing:
    print("Waiting for DAGs from the Airflow Bundles: " + ", ".join(missing), file=sys.stderr)
    sys.exit(1)

for bundle in expected:
    print(f"Verified Bundle {bundle}: " + ", ".join(sorted(dags[bundle])))
    unprefixed = sorted(dag_id for dag_id in dags[bundle] if not dag_id.startswith(bundle + "-"))
    if unprefixed:
        print(f"WARNING: DAG IDs in {bundle} not starting with {bundle}- get no writer token: " + ", ".join(unprefixed))
'; then
    import_errors="$("${AIRFLOW_COMPOSE[@]}" exec -T airflow-dag-processor airflow dags list-import-errors --output json 2>/dev/null || true)"
    if [[ -n "$import_errors" ]]; then
      printf '%s' "$import_errors" | python3 -c '
import json
import sys

try:
    errors = json.load(sys.stdin)
except json.JSONDecodeError:
    print("WARNING: Could not parse Airflow import-error report.")
    sys.exit(0)

if isinstance(errors, list):
    for error in errors:
        if isinstance(error, dict):
            bundle = error.get("bundle_name", "unknown bundle")
            path = error.get("filepath", "unknown file")
            print(f"WARNING: Airflow import error in {bundle}:{path}; DAG registration was verified separately.")
'
    fi
    exit 0
  fi
  sleep 5
done

echo "Timed out waiting for DAGs from every product Bundle after ${timeout_seconds}s." >&2
echo "Inspect airflow-dag-processor logs and run the airflow dags list-import-errors command inside that service." >&2
exit 1
