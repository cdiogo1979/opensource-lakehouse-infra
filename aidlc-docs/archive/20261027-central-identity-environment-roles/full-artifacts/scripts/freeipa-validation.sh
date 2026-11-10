#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

env_file_value() {
  local key="$1"
  if [[ -f .env ]]; then
    sed -n "s/^${key}=//p" .env | tail -n 1
  fi
}

subnet="${FREEIPA_VALIDATION_SUBNET:-$(env_file_value FREEIPA_VALIDATION_SUBNET)}"
server_ip="${FREEIPA_VALIDATION_IP:-$(env_file_value FREEIPA_VALIDATION_IP)}"
subnet="${subnet:-172.30.250.0/24}"
server_ip="${server_ip:-172.30.250.10}"
hostname="${FREEIPA_HOSTNAME:-$(env_file_value FREEIPA_HOSTNAME)}"
hostname="${hostname:-ipa.lakehouse.local}"
export FREEIPA_VALIDATION_SUBNET="${subnet}"
export FREEIPA_VALIDATION_IP="${server_ip}"
export FREEIPA_HOSTNAME="${hostname}"

# Compose interpolates the complete file even when only the validation profile
# is selected. Supply harmless local defaults for unrelated Airflow services so
# FreeIPA-only operator commands do not depend on Airflow's environment.
airflow_uid="${AIRFLOW_UID:-$(env_file_value AIRFLOW_UID)}"
export AIRFLOW_UID="${airflow_uid:-$(id -u)}"
docker_gid="${DOCKER_GID:-$(env_file_value DOCKER_GID)}"
export DOCKER_GID="${docker_gid:-0}"
project_root="${LAKEHOUSE_PROJECT_ROOT:-$(env_file_value LAKEHOUSE_PROJECT_ROOT)}"
export LAKEHOUSE_PROJECT_ROOT="${project_root:-${ROOT_DIR}}"
bundle_host_root="${LAKEHOUSE_BUNDLE_HOST_ROOT:-$(env_file_value LAKEHOUSE_BUNDLE_HOST_ROOT)}"
export LAKEHOUSE_BUNDLE_HOST_ROOT="${bundle_host_root:-${ROOT_DIR}}"
bundle_container_root="${LAKEHOUSE_BUNDLE_CONTAINER_ROOT:-$(env_file_value LAKEHOUSE_BUNDLE_CONTAINER_ROOT)}"
export LAKEHOUSE_BUNDLE_CONTAINER_ROOT="${bundle_container_root:-/opt/lakehouse-bundle}"

case "${1:-}" in
  start)
    if [[ ! -s .runtime/credentials/freeipa-server-install-options ]]; then
      echo "FreeIPA bootstrap files are missing; run scripts/bootstrap-local.sh first." >&2
      exit 2
    fi
    python3 infra/freeipa/check-network.py \
      "${FREEIPA_VALIDATION_SUBNET}" "${FREEIPA_VALIDATION_IP}" \
      iceberg-poc-freeipa-validation-net
    docker compose --profile freeipa-validation up -d --build --wait --wait-timeout 1800 freeipa-validation
    ;;
  status)
    docker compose --profile freeipa-validation ps freeipa-validation
    ;;
  stop)
    docker compose --profile freeipa-validation stop freeipa-validation
    ;;
  bootstrap-identities)
    docker compose --profile freeipa-validation exec freeipa-validation \
      /usr/local/sbin/freeipa-bootstrap-identities
    ;;
  role-member)
    if [[ $# -ne 4 ]]; then
      echo "Usage: scripts/freeipa-validation.sh role-member USER GROUP add|remove" >&2
      exit 2
    fi
    docker compose --profile freeipa-validation exec freeipa-validation \
      /usr/local/sbin/freeipa-set-role-membership "$2" "$3" "$4"
    ;;
  *)
    echo "Usage: scripts/freeipa-validation.sh {start|status|stop|bootstrap-identities|role-member USER GROUP add|remove}" >&2
    exit 2
    ;;
esac
