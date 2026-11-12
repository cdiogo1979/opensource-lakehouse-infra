#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
# With the containerd image store, BuildKit adds a timestamped provenance attestation
# to every build, giving cached builds a new image ID and making Compose recreate
# running containers on every start. Builds here are local, so leave it out.
export BUILDX_NO_DEFAULT_ATTESTATIONS=1
# Each command passes only the enabled module files, so Compose would report the
# other modules' containers as orphans and suggest --remove-orphans, which would
# delete them. The modules are deliberately separate files of one project.
export COMPOSE_IGNORE_ORPHANS=true
TIMEOUT_SECONDS="${STARTUP_TIMEOUT_SECONDS:-600}"
SERVICES=(keycloak-db polaris-db rustfs ldap keycloak polaris)
STARROCKS_SERVICES=(starrocks-fe starrocks-be)
AIRFLOW_SERVICES=(airflow-postgres airflow-api-server airflow-scheduler airflow-dag-processor airflow-triggerer airflow-token-broker)

if [[ -f .env ]]; then
  while IFS='=' read -r key value; do
    if [[ "$key" == JUPYTERHUB_HOST_PORT && -z "${JUPYTERHUB_HOST_PORT:-}" ]]; then JUPYTERHUB_HOST_PORT="$value"; fi
    if [[ "$key" == JUPYTER_ENABLED && -z "${JUPYTER_ENABLED:-}" ]]; then JUPYTER_ENABLED="$value"; fi
    if [[ "$key" == JENKINS_ENABLED && -z "${JENKINS_ENABLED:-}" ]]; then JENKINS_ENABLED="$value"; fi
    if [[ "$key" == STARROCKS_ENABLED && -z "${STARROCKS_ENABLED:-}" ]]; then STARROCKS_ENABLED="$value"; fi
  done < .env
fi
JUPYTERHUB_HOST_PORT="${JUPYTERHUB_HOST_PORT:-8000}"
enabled() { [[ "$(printf '%s' "${1:-true}" | tr '[:upper:]' '[:lower:]')" != false ]] && echo true || echo false; }
JUPYTER_ENABLED="$(enabled "${JUPYTER_ENABLED:-}")"
JENKINS_ENABLED="$(enabled "${JENKINS_ENABLED:-}")"
STARROCKS_ENABLED="$(enabled "${STARROCKS_ENABLED:-}")"
export JUPYTERHUB_HOST_PORT JUPYTER_ENABLED JENKINS_ENABLED STARROCKS_ENABLED

# Core always runs; each optional module adds its Compose file and services.
MODULE_FILES=()
if [[ "$JUPYTER_ENABLED" == true ]]; then MODULE_FILES+=(-f compose.jupyter.yml); SERVICES+=(jupyterhub); fi
if [[ "$JENKINS_ENABLED" == true ]]; then MODULE_FILES+=(-f compose.jenkins.yml); SERVICES+=(jenkins); fi
if [[ "$STARROCKS_ENABLED" == true ]]; then MODULE_FILES+=(-f compose.starrocks.yml); SERVICES+=("${STARROCKS_SERVICES[@]}"); fi
# ${arr[@]+...} keeps an empty array safe under set -u in bash 3.2.
COMPOSE=(docker compose -f compose.core.yml ${MODULE_FILES[@]+"${MODULE_FILES[@]}"})
AIRFLOW_COMPOSE=("${COMPOSE[@]}" -f compose.airflow.yml --profile airflow)
# The scheduled reconciler (Keycloak groups to Polaris and StarRocks) is set up by the product
# bootstrap; once it exists, start and stop manage it with the rest of the stack.
RECONCILER_COMPOSE=(docker compose -f compose.core.yml --profile scheduled-reconciliation)
reconciler_exists() { docker inspect lakehouse-local-polaris-group-reconciler-1 >/dev/null 2>&1; }

usage() { echo "Usage: scripts/lakehouse.sh {start|status|stop|start-airflow|airflow-status|stop-airflow|reconcile-starrocks [--dry-run]|rotate-checkpoint-keys [--product FILE]|reset [--yes|--dry-run]}" >&2; }

# The staged checkpoint keys are bind-mounted into the Hub and the Airflow scheduler; create the
# folder first so Docker never creates it, and say which buckets still lack a key.
prepare_checkpoint_keys() {
  mkdir -p "$ROOT_DIR/.runtime/container-mounts/checkpoint-keys"
  chmod 755 "$ROOT_DIR/.runtime/container-mounts/checkpoint-keys"
  python3 infra/rustfs/bootstrap-checkpoint-keys.py --check-staged
}

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
  # The scheduled sync (optional profile): unhealthy means no cycle succeeded lately.
  state="$(docker inspect --format '{{.State.Status}}{{if .State.Health}} ({{.State.Health.Status}}){{end}}' lakehouse-local-polaris-group-reconciler-1 2>/dev/null || true)"
  if [[ -n "$state" ]]; then printf '%-16s %s\n' "reconciler" "$state"; fi
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
  python3 scripts/setup/prepare-runtime.py
  # Airflow runs and the Spark smoke checks use the shared Spark runtime image.
  docker build -t local/lakehouse-spark-runtime:3.5.5_1.10.2 -f infra/spark-runtime/Dockerfile .
  if [[ "$JUPYTER_ENABLED" == true ]]; then
    python3 scripts/setup/prepare-jupyterhub-broker-certificates.py
    JUPYTERHUB_BROKER_CA_HOST_PATH="$ROOT_DIR/.runtime/container-mounts/jupyterhub-broker-ca.crt"
    JUPYTERHUB_CHECKPOINT_KEYS_HOST_DIR="$ROOT_DIR/.runtime/container-mounts/checkpoint-keys"
    export JUPYTERHUB_BROKER_CA_HOST_PATH JUPYTERHUB_CHECKPOINT_KEYS_HOST_DIR
    python3 scripts/setup/check-jupyter-user-network.py
    python3 scripts/setup/validate-jupyterhub-credentials.py
    # A first bootstrap starts the stack before the keys exist; spawns then fail only for those buckets.
    prepare_checkpoint_keys || echo "NOTICE: Jupyter servers of the products above get no checkpoint key until the product bootstrap runs."
    docker build -t local/lakehouse-jupyter-singleuser:6.1.1-spark \
      -f infra/jupyter/singleuser/Dockerfile .
    "${COMPOSE[@]}" build jupyterhub
  fi
  "${COMPOSE[@]}" up -d --build keycloak-db polaris-db rustfs ldap
  wait_for_services keycloak-db polaris-db rustfs ldap
  "${COMPOSE[@]}" --profile schema-init run --rm polaris-schema-init
  "${COMPOSE[@]}" up -d keycloak polaris
  wait_for_services keycloak polaris
  python3 infra/keycloak/bootstrap-realm.py
  if [[ "$JUPYTER_ENABLED" == true ]]; then
    "${COMPOSE[@]}" up -d jupyterhub
    wait_for_services jupyterhub
  else
    echo "NOTICE: JupyterHub is disabled (JUPYTER_ENABLED=false); not started."
  fi
  if [[ "$JENKINS_ENABLED" == true ]]; then
    "${COMPOSE[@]}" build jenkins
    "${COMPOSE[@]}" up -d jenkins
    wait_for_services jenkins
  else
    echo "NOTICE: Jenkins is disabled (JENKINS_ENABLED=false); not started."
  fi
  if [[ "$STARROCKS_ENABLED" == true ]]; then
    python3 scripts/setup/prepare-starrocks-certificates.py
    "${COMPOSE[@]}" up -d "${STARROCKS_SERVICES[@]}"
    wait_for_services "${STARROCKS_SERVICES[@]}"
    python3 infra/starrocks/bootstrap-starrocks.py --runtime-only
    echo "StarRocks is ready. SQL: 127.0.0.1:${STARROCKS_QUERY_PORT:-9030} (log in with scripts/clients/starrocks-login.sh <user>)."
  else
    echo "NOTICE: StarRocks is disabled (STARROCKS_ENABLED=false); not started."
  fi
  if reconciler_exists; then
    "${RECONCILER_COMPOSE[@]}" up -d polaris-group-reconciler
  else
    echo "NOTICE: the scheduled reconciler is not set up yet; scripts/bootstrap-default-product.sh starts it."
  fi
  echo "Core providers are ready. Keycloak: http://127.0.0.1:${KEYCLOAK_HOST_PORT:-8080}; Polaris: http://127.0.0.1:${POLARIS_HOST_PORT:-8181}; RustFS console: http://127.0.0.1:${RUSTFS_CONSOLE_HOST_PORT:-9001}."
  if [[ "$JUPYTER_ENABLED" == true ]]; then echo "JupyterHub: http://jupyterhub.localhost:${JUPYTERHUB_HOST_PORT}"; fi
  if [[ "$JENKINS_ENABLED" == true ]]; then echo "Jenkins: http://127.0.0.1:${JENKINS_HOST_PORT:-8090}"; fi
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
  # Airflow clones its Git Bundles into this repository; the workload repository is not referenced locally.
  LAKEHOUSE_BUNDLE_HOST_ROOT="${LAKEHOUSE_BUNDLE_HOST_ROOT:-${ROOT_DIR}/.runtime/airflow-dag-bundles}"
  LAKEHOUSE_BUNDLE_CONTAINER_ROOT="${LAKEHOUSE_BUNDLE_CONTAINER_ROOT:-/opt/airflow/dag_bundles}"
  LAKEHOUSE_BROKER_CA_HOST_PATH="${LAKEHOUSE_BROKER_CA_HOST_PATH:-${ROOT_DIR}/.runtime/container-mounts/airflow-token-broker-ca.crt}"
  LAKEHOUSE_CHECKPOINT_KEYS_HOST_DIR="${ROOT_DIR}/.runtime/container-mounts/checkpoint-keys"
  LAKEHOUSE_BUNDLE_CONFIG_LIST="$(python3 scripts/setup/airflow-bundle-config.py)"
  AIRFLOW_HOST_PORT="${AIRFLOW_HOST_PORT:-8085}"
  export AIRFLOW_UID DOCKER_GID LAKEHOUSE_BUNDLE_HOST_ROOT
  export LAKEHOUSE_BUNDLE_CONTAINER_ROOT LAKEHOUSE_BROKER_CA_HOST_PATH LAKEHOUSE_CHECKPOINT_KEYS_HOST_DIR LAKEHOUSE_BUNDLE_CONFIG_LIST AIRFLOW_HOST_PORT
}

airflow_service_state() {
  local service="$1" container
  container="$("${AIRFLOW_COMPOSE[@]}" ps -q "$service")"
  if [[ -z "$container" ]]; then echo stopped; return; fi
  docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container" 2>/dev/null || echo unavailable
}

show_airflow_status() {
  local service state
  for service in keycloak-db polaris-db rustfs ldap keycloak polaris "${AIRFLOW_SERVICES[@]}"; do
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
  python3 scripts/setup/prepare-runtime.py
  bash scripts/setup/provision-airflow-secrets.sh
  python3 scripts/setup/prepare-airflow-broker-certificates.py
  # Every run mounts its product environment's checkpoint key; refuse to start without them.
  prepare_checkpoint_keys
  local fingerprint recorded
  # Bundles and broker writers follow data-products/*.yaml; the broker reads its writers only at start.
  fingerprint="$(python3 scripts/setup/stage-airflow-writers.py)"
  recorded="$(python3 scripts/setup/airflow-bundle-state.py read)"
  python3 infra/airflow/validate-bundle-config.py --host-paths
  # Airflow applies sparse_dirs only on the first clone; update existing checkouts.
  python3 scripts/setup/sync-bundle-checkouts.py
  "${COMPOSE[@]}" up -d --build keycloak-db polaris-db rustfs ldap
  wait_for_services keycloak-db polaris-db rustfs ldap
  "${COMPOSE[@]}" --profile schema-init run --rm polaris-schema-init
  "${COMPOSE[@]}" up -d keycloak polaris
  wait_for_services keycloak polaris
  python3 infra/keycloak/bootstrap-realm.py \
    --airflow-secret-file .runtime/credentials/keycloak-airflow-client-secret
  docker build -t local/lakehouse-spark-runtime:3.5.5_1.10.2 -f infra/spark-runtime/Dockerfile .
  "${AIRFLOW_COMPOSE[@]}" up --build -d airflow-api-server airflow-scheduler airflow-dag-processor airflow-triggerer airflow-token-broker
  if [[ "$fingerprint" != "$recorded" ]]; then
    "${AIRFLOW_COMPOSE[@]}" up -d --no-deps --force-recreate airflow-token-broker
  fi
  wait_for_airflow_services airflow-postgres airflow-api-server airflow-scheduler airflow-dag-processor airflow-triggerer airflow-token-broker
  AIRFLOW_DAG_VERIFY_TIMEOUT_SECONDS="$TIMEOUT_SECONDS" bash scripts/verify/airflow-dags.sh
  python3 scripts/setup/airflow-bundle-state.py record "$fingerprint"
  echo "Airflow is ready at http://127.0.0.1:${AIRFLOW_HOST_PORT}; each data product's production and UAT Bundles are registered (no DAG was run)."
}

case "${1:-}" in
  start) start_stack ;;
  reset) require_tools; python3 scripts/operations/reset-lakehouse.py "${@:2}" ;;
  reconcile-starrocks) require_tools; python3 infra/starrocks/reconcile-starrocks-users.py "${@:2}" ;;
  rotate-checkpoint-keys) require_tools; python3 infra/rustfs/bootstrap-checkpoint-keys.py --rotate "${@:2}" ;;
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
    # First, so it doesn't run its cycle against services that are stopping.
    if reconciler_exists; then "${RECONCILER_COMPOSE[@]}" stop polaris-group-reconciler; fi
    if [[ "$STARROCKS_ENABLED" == true ]]; then "${COMPOSE[@]}" stop starrocks-be starrocks-fe; fi
    if [[ "$JENKINS_ENABLED" == true ]]; then "${COMPOSE[@]}" stop jenkins; fi
    if [[ "$JUPYTER_ENABLED" == true ]]; then "${COMPOSE[@]}" stop jupyterhub; fi
    "${COMPOSE[@]}" stop keycloak polaris rustfs ldap polaris-db keycloak-db
    echo "The scheduled reconciler, enabled modules and core services stopped; named volumes and RustFS objects were preserved."
    ;;
  *) usage; exit 2 ;;
esac
