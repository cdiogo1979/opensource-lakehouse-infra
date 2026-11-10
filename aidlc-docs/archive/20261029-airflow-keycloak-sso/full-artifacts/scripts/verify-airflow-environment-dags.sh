#!/usr/bin/env bash
set -euo pipefail

# Verify that Airflow has parsed the maintained UAT and production DAG Bundles.
# Production DAGs are supplied by lakehouse-main and use the `main-` DAG ID prefix.
timeout_seconds="${AIRFLOW_DAG_VERIFY_TIMEOUT_SECONDS:-300}"
AIRFLOW_COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.airflow.yml --profile airflow)
if ! [[ "$timeout_seconds" =~ ^[1-9][0-9]*$ ]]; then
  echo "AIRFLOW_DAG_VERIFY_TIMEOUT_SECONDS must be a positive integer" >&2
  exit 2
fi

deadline=$((SECONDS + timeout_seconds))
while (( SECONDS < deadline )); do
  if dag_json="$("${AIRFLOW_COMPOSE[@]}" exec -T airflow-dag-processor airflow dags list --output json 2>/dev/null || true)" \
    && printf '%s' "$dag_json" | python3 -c '
import json
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

expected = {
    "lakehouse-main": "main-test_environment",
    "lakehouse-uat": "uat-test_environment",
}
found = {(row.get("bundle_name"), row.get("dag_id")) for row in rows if isinstance(row, dict)}
missing = [f"{bundle}:{dag_id}" for bundle, dag_id in expected.items() if (bundle, dag_id) not in found]
if missing:
    print("Waiting for Airflow DAGs: " + ", ".join(missing), file=sys.stderr)
    sys.exit(1)

print("Verified production DAG main-test_environment from lakehouse-main.")
print("Verified UAT DAG uat-test_environment from lakehouse-uat.")
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

echo "Timed out waiting for production and UAT DAGs after ${timeout_seconds}s." >&2
echo "Inspect airflow-dag-processor logs and run the airflow dags list-import-errors command inside that service." >&2
exit 1
