#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

readonly preflight_container=iceberg-poc-starrocks-preflight
compose=(docker compose --profile starrocks)

"${compose[@]}" build starrocks-preflight starrocks-fe starrocks-be

if ! docker inspect --format '{{.State.Status}}' "$preflight_container" >/dev/null 2>&1; then
  :
else
  preflight_status="$(docker inspect --format '{{.State.Status}}' "$preflight_container")"
  preflight_exit="$(docker inspect --format '{{.State.ExitCode}}' "$preflight_container")"
  if [[ "$preflight_status" != exited ]]; then
    echo "StarRocks startup blocked: previous preflight container is not exited; inspect it before continuing." >&2
    exit 1
  fi
  if [[ "$preflight_exit" != 0 ]]; then
    echo "StarRocks startup blocked: previous preflight failed and was preserved for inspection." >&2
    exit 1
  fi
  docker rm "$preflight_container" >/dev/null
fi

for shared_container in iceberg-poc-kdc; do
  if ! docker inspect --format '{{.State.Health.Status}}' "$shared_container" 2>/dev/null | grep -qx healthy; then
    echo "StarRocks startup blocked: required shared service '$shared_container' must already be healthy. Start it using the normal platform workflow." >&2
    exit 1
  fi
done

"${compose[@]}" up --no-deps --abort-on-container-exit --exit-code-from starrocks-preflight starrocks-preflight

"${compose[@]}" up --no-deps -d --wait --wait-timeout 300 starrocks-fe
"${compose[@]}" up --no-deps -d --wait --wait-timeout 300 starrocks-be
"${ROOT_DIR}/scripts/verify-starrocks-sql-secret-safety.sh"
python3 "${ROOT_DIR}/infra/starrocks/sql-bootstrap/runner.py" ensure-backend

echo "StarRocks FE and BE are healthy. FE UI: http://127.0.0.1:8030; SQL: 127.0.0.1:9030."
