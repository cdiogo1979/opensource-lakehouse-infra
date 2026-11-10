#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
COMPOSE=(docker compose -f docker-compose.yml)
TIMEOUT_SECONDS="${STARTUP_TIMEOUT_SECONDS:-600}"
SERVICES=(keycloak-db polaris-db rustfs keycloak polaris)

usage() { echo "Usage: scripts/lakehouse.sh {start|status|stop}" >&2; }

require_tools() {
  command -v docker >/dev/null 2>&1 || { echo "ERROR: Docker is required." >&2; return 1; }
  docker compose version >/dev/null 2>&1 || { echo "ERROR: Docker Compose V2 is required." >&2; return 1; }
  command -v python3 >/dev/null 2>&1 || { echo "ERROR: Python 3 is required." >&2; return 1; }
}

service_state() {
  local service="$1" container
  container="$("${COMPOSE[@]}" ps -q "$service")"
  if [[ -z "$container" ]]; then echo stopped; return; fi
  docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container" 2>/dev/null || echo unavailable
}

show_status() {
  local service state
  for service in "${SERVICES[@]}"; do
    state="$(service_state "$service")"
    printf '%-16s %s\n' "$service" "$state"
  done
}

wait_for_services() {
  local start=$SECONDS service state all_ready
  while true; do
    all_ready=true
    for service in "$@"; do
      state="$(service_state "$service")"
      [[ "$state" == healthy ]] || all_ready=false
    done
    [[ "$all_ready" == true ]] && return 0
    if (( SECONDS - start >= TIMEOUT_SECONDS )); then
      echo "ERROR: Readiness timed out after ${TIMEOUT_SECONDS}s. Provider state:" >&2
      show_status >&2
      return 1
    fi
    sleep 3
  done
}

start_stack() {
  require_tools
  if ! [[ "$TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: STARTUP_TIMEOUT_SECONDS must be a positive integer." >&2
    return 2
  fi
  python3 scripts/prepare-lakehouse-runtime.py
  "${COMPOSE[@]}" up -d keycloak-db polaris-db rustfs
  wait_for_services keycloak-db polaris-db rustfs
  "${COMPOSE[@]}" --profile schema-init run --rm polaris-schema-init
  "${COMPOSE[@]}" up -d keycloak polaris
  wait_for_services keycloak polaris
  echo "Core providers are ready. Keycloak: http://127.0.0.1:${KEYCLOAK_HOST_PORT:-8080}; Polaris: http://127.0.0.1:${POLARIS_HOST_PORT:-8181}; RustFS console: http://127.0.0.1:${RUSTFS_CONSOLE_HOST_PORT:-9001}."
}

case "${1:-}" in
  start) start_stack ;;
  status) require_tools; show_status ;;
  stop)
    require_tools
    "${COMPOSE[@]}" stop "${SERVICES[@]}"
    echo "Core services stopped; named volumes and RustFS objects were preserved."
    ;;
  *) usage; exit 2 ;;
esac
