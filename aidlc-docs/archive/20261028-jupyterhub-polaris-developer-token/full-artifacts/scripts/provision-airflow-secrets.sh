#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CREDENTIAL_DIR="${ROOT_DIR}/.runtime/credentials"

command -v openssl >/dev/null 2>&1 || {
  echo "ERROR: openssl is required to provision Airflow secrets." >&2
  exit 1
}

mkdir -p "${CREDENTIAL_DIR}" "${ROOT_DIR}/.runtime/airflow-dag-bundles"
chmod 700 "${ROOT_DIR}/.runtime" "${CREDENTIAL_DIR}" "${ROOT_DIR}/.runtime/airflow-dag-bundles"
umask 077

create_secret_if_absent() {
  local name="$1"
  local generator="$2"
  local path="${CREDENTIAL_DIR}/${name}"
  local temporary="${path}.tmp.$$"

  if [[ -L "${path}" ]]; then
    echo "ERROR: Refusing to use a symlink for Airflow secret ${name}." >&2
    return 1
  fi
  if [[ -e "${path}" ]]; then
    if [[ ! -s "${path}" ]]; then
      echo "ERROR: Existing Airflow secret ${name} is empty; refusing to replace it." >&2
      return 1
    fi
    local mode
    mode="$(stat -f '%Lp' "${path}" 2>/dev/null || stat -c '%a' "${path}")"
    if [[ "${mode}" != "600" ]]; then
      echo "ERROR: Existing Airflow secret ${name} must have mode 0600; refusing to change it." >&2
      return 1
    fi
    return 0
  fi

  case "${generator}" in
    hex32) openssl rand -hex 32 > "${temporary}" ;;
    fernet)
      openssl rand -base64 32 | tr '+/' '-_' > "${temporary}"
      ;;
    *) echo "ERROR: Unknown Airflow secret generator." >&2; return 1 ;;
  esac
  chmod 600 "${temporary}"
  if ! ln "${temporary}" "${path}" 2>/dev/null; then
    rm -f "${temporary}"
    if [[ ! -s "${path}" ]]; then
      echo "ERROR: Could not create Airflow secret ${name}." >&2
      return 1
    fi
  else
    rm -f "${temporary}"
  fi

  if [[ ! -s "${path}" ]]; then
    echo "ERROR: Generated Airflow secret ${name} is empty." >&2
    return 1
  fi
  chmod 600 "${path}"
}

create_secret_if_absent airflow-admin-password hex32
create_secret_if_absent airflow-api-secret-key hex32
create_secret_if_absent airflow-fernet-key fernet
create_secret_if_absent airflow-jwt-secret hex32
create_secret_if_absent airflow-postgres-password hex32

echo "Airflow secret files are ready under .runtime/credentials; values were not displayed."
