#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
COMPOSE=(docker compose -f docker-compose.yml)
AIRFLOW_COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.airflow.yml --profile airflow)
TIMEOUT_SECONDS="${STARTUP_TIMEOUT_SECONDS:-600}"
SERVICES=(keycloak-db polaris-db rustfs keycloak polaris jupyterhub jenkins)
AIRFLOW_SERVICES=(airflow-postgres airflow-api-server airflow-scheduler airflow-dag-processor airflow-triggerer airflow-token-broker)

if [[ -z "${JUPYTERHUB_HOST_PORT:-}" && -f .env ]]; then
  while IFS='=' read -r key value; do
    if [[ "$key" == JUPYTERHUB_HOST_PORT ]]; then JUPYTERHUB_HOST_PORT="$value"; fi
  done < .env
fi
JUPYTERHUB_HOST_PORT="${JUPYTERHUB_HOST_PORT:-8000}"
export JUPYTERHUB_HOST_PORT

usage() { echo "Usage: scripts/lakehouse.sh {start|status|stop|start-airflow|airflow-status|stop-airflow|remove-legacy-jenkins --confirm}" >&2; }

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
  python3 scripts/prepare-jupyterhub-broker-certificates.py
  JUPYTERHUB_BROKER_CA_HOST_PATH="$ROOT_DIR/.runtime/container-mounts/jupyterhub-broker-ca.crt"
  export JUPYTERHUB_BROKER_CA_HOST_PATH
  python3 scripts/check-jupyter-user-network.py
  python3 scripts/validate-jupyterhub-credentials.py
  docker build -t local/lakehouse-spark-runtime:3.5.5_1.10.2 -f infra/spark-runtime/Dockerfile .
  docker build -t local/lakehouse-jupyter-singleuser:6.1.1-spark \
    -f infra/jupyter/singleuser/Dockerfile .
  "${COMPOSE[@]}" build jupyterhub
  "${COMPOSE[@]}" up -d keycloak-db polaris-db rustfs
  wait_for_services keycloak-db polaris-db rustfs
  "${COMPOSE[@]}" --profile schema-init run --rm polaris-schema-init
  "${COMPOSE[@]}" up -d keycloak polaris
  wait_for_services keycloak polaris
  python3 infra/keycloak/bootstrap-realm.py
  "${COMPOSE[@]}" up -d jupyterhub
  wait_for_services jupyterhub
  "${COMPOSE[@]}" build jenkins
  python3 scripts/migrate-jenkins-home.py
  "${COMPOSE[@]}" up -d jenkins
  wait_for_services jenkins
  echo "Core providers, JupyterHub, and Jenkins are ready. JupyterHub: http://jupyterhub.localhost:${JUPYTERHUB_HOST_PORT}; Keycloak: http://127.0.0.1:${KEYCLOAK_HOST_PORT:-8080}; Polaris: http://127.0.0.1:${POLARIS_HOST_PORT:-8181}; RustFS console: http://127.0.0.1:${RUSTFS_CONSOLE_HOST_PORT:-9001}; Jenkins: http://127.0.0.1:${JENKINS_HOST_PORT:-8090}."
}

remove_legacy_jenkins() {
  # Removes only the pre-v2 Jenkins container and its home volume after the v2
  # home has been verified as a copy of it. The unrelated jenkins_home volume
  # and all images are never touched.
  local legacy_container=hive-dremio-rustfs-jenkins-1 legacy_volume=iceberg-poc-jenkins-home marker state
  require_tools
  if [[ "${1:-}" != "--confirm" ]]; then
    echo "ERROR: remove-legacy-jenkins deletes ${legacy_container} and ${legacy_volume}; rerun with --confirm." >&2
    return 2
  fi
  marker="$(docker run --rm --entrypoint cat -v lakehouse-local_jenkins-home:/h:ro local/lakehouse-jenkins:2.580.1 /h/.lakehouse-home-origin 2>/dev/null || true)"
  if [[ "$marker" != "migrated:${legacy_volume} "* ]]; then
    echo "ERROR: the v2 Jenkins home is not a verified copy of ${legacy_volume}; nothing removed." >&2
    return 1
  fi
  state="$(service_state jenkins)"
  if [[ "$state" != healthy ]]; then
    echo "ERROR: v2 Jenkins is ${state}, not healthy; nothing removed." >&2
    return 1
  fi
  if [[ "$(docker inspect --format '{{.State.Running}}' "$legacy_container" 2>/dev/null || true)" == true ]]; then
    echo "ERROR: ${legacy_container} is running; stop it first. Nothing removed." >&2
    return 1
  fi
  if docker inspect "$legacy_container" >/dev/null 2>&1; then
    docker rm "$legacy_container" >/dev/null
    echo "Removed container ${legacy_container}."
  fi
  if docker volume inspect "$legacy_volume" >/dev/null 2>&1; then
    docker volume rm "$legacy_volume" >/dev/null
    echo "Removed volume ${legacy_volume}."
  fi
}

prepare_airflow_environment() {
  AIRFLOW_UID="${AIRFLOW_UID:-$(id -u)}"
  if [[ -z "${DOCKER_GID:-}" ]]; then
    if [[ "$(uname -s)" == Darwin ]]; then
      # Docker Desktop exposes its VM socket inside containers as root:102;
      # macOS stat reports the host-side socket group (typically staff, gid 1).
      DOCKER_GID=102
    else
      DOCKER_GID="$(stat -c '%g' /var/run/docker.sock 2>/dev/null || stat -f '%g' /var/run/docker.sock 2>/dev/null || printf '0')"
    fi
  fi
  LAKEHOUSE_PROJECT_ROOT="${LAKEHOUSE_PROJECT_ROOT:-$(cd "${ROOT_DIR}/../opensource-lakehouse" && pwd)}"
  LAKEHOUSE_BUNDLE_HOST_ROOT="${LAKEHOUSE_BUNDLE_HOST_ROOT:-${LAKEHOUSE_PROJECT_ROOT}/.runtime/airflow-dag-bundles}"
  LAKEHOUSE_BUNDLE_CONTAINER_ROOT="${LAKEHOUSE_BUNDLE_CONTAINER_ROOT:-/opt/airflow/dag_bundles}"
  LAKEHOUSE_BROKER_CA_HOST_PATH="${LAKEHOUSE_BROKER_CA_HOST_PATH:-${ROOT_DIR}/.runtime/container-mounts/airflow-token-broker-ca.crt}"
  LAKEHOUSE_BUNDLE_CONFIG_LIST="$(python3 scripts/airflow-bundle-config.py)"
  AIRFLOW_HOST_PORT="${AIRFLOW_HOST_PORT:-8085}"
  export AIRFLOW_UID DOCKER_GID LAKEHOUSE_PROJECT_ROOT LAKEHOUSE_BUNDLE_HOST_ROOT
  export LAKEHOUSE_BUNDLE_CONTAINER_ROOT LAKEHOUSE_BROKER_CA_HOST_PATH LAKEHOUSE_BUNDLE_CONFIG_LIST AIRFLOW_HOST_PORT
}

airflow_service_state() {
  local service="$1" container
  container="$("${AIRFLOW_COMPOSE[@]}" ps -q "$service")"
  if [[ -z "$container" ]]; then echo stopped; return; fi
  docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container" 2>/dev/null || echo unavailable
}

show_airflow_status() {
  local service state
  for service in keycloak-db polaris-db rustfs keycloak polaris "${AIRFLOW_SERVICES[@]}"; do
    state="$(airflow_service_state "$service")"
    printf '%-24s %s\n' "$service" "$state"
  done
}

wait_for_airflow_services() {
  local start=$SECONDS service state all_ready
  while true; do
    all_ready=true
    for service in "$@"; do
      state="$(airflow_service_state "$service")"
      # The scheduler, DAG processor, and triggerer do not define Docker
      # healthchecks; their running state is the available readiness signal.
      [[ "$state" == healthy || "$state" == running ]] || all_ready=false
    done
    [[ "$all_ready" == true ]] && return 0
    if (( SECONDS - start >= TIMEOUT_SECONDS )); then
      echo "ERROR: Airflow readiness timed out after ${TIMEOUT_SECONDS}s." >&2
      show_airflow_status >&2
      return 1
    fi
    sleep 3
  done
}

start_airflow() {
  require_tools
  if ! [[ "$TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: STARTUP_TIMEOUT_SECONDS must be a positive integer." >&2
    return 2
  fi
  prepare_airflow_environment
  python3 scripts/prepare-lakehouse-runtime.py
  bash scripts/provision-airflow-secrets.sh
  python3 scripts/prepare-airflow-token-broker-certificates.py
  python3 infra/airflow/validate-bundle-config.py
  "${COMPOSE[@]}" up -d keycloak-db polaris-db rustfs
  wait_for_services keycloak-db polaris-db rustfs
  "${COMPOSE[@]}" --profile schema-init run --rm polaris-schema-init
  "${COMPOSE[@]}" up -d keycloak polaris
  wait_for_services keycloak polaris
  python3 infra/keycloak/bootstrap-realm.py \
    --airflow-secret-file .runtime/credentials/keycloak-airflow-client-secret
  docker build -t local/lakehouse-spark-runtime:3.5.5_1.10.2 -f infra/spark-runtime/Dockerfile .
  "${AIRFLOW_COMPOSE[@]}" up --build -d airflow-api-server airflow-scheduler airflow-dag-processor airflow-triggerer airflow-token-broker
  wait_for_airflow_services airflow-postgres airflow-api-server airflow-scheduler airflow-dag-processor airflow-triggerer airflow-token-broker
  AIRFLOW_DAG_VERIFY_TIMEOUT_SECONDS="$TIMEOUT_SECONDS" bash scripts/verify-airflow-environment-dags.sh
  echo "Airflow is ready at http://127.0.0.1:${AIRFLOW_HOST_PORT}; production and UAT Bundles are registered (no DAG was run)."
}

case "${1:-}" in
  start) start_stack ;;
  remove-legacy-jenkins) remove_legacy_jenkins "${2:-}" ;;
  status) require_tools; show_status ;;
  start-airflow) start_airflow ;;
  airflow-status)
    require_tools
    prepare_airflow_environment
    show_airflow_status
    ;;
  stop-airflow)
    require_tools
    prepare_airflow_environment
    spark_runs="$(docker ps -aq --filter label=lakehouse-local.role=airflow-spark-run)"
    if [[ -n "$spark_runs" ]]; then docker rm --force $spark_runs >/dev/null; fi
    "${AIRFLOW_COMPOSE[@]}" stop "${AIRFLOW_SERVICES[@]}" airflow-init
    echo "Airflow and its Spark runs stopped; provider data, metadata volume, and Bundle checkouts were preserved."
    ;;
  stop)
    require_tools
    user_servers="$(docker ps -aq --filter label=lakehouse-local.role=jupyter-user-server)"
    if [[ -n "$user_servers" ]]; then
      # These containers have separately named home volumes; omitting -v retains user data.
      docker rm --force $user_servers >/dev/null
    fi
    "${COMPOSE[@]}" stop jenkins jupyterhub
    "${COMPOSE[@]}" stop keycloak polaris rustfs polaris-db keycloak-db
    echo "Jenkins, JupyterHub, and core services stopped; named volumes and RustFS objects were preserved."
    ;;
  *) usage; exit 2 ;;
esac
