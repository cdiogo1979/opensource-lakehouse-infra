#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

echo "This removes only this project's Dremio container/data volume, Dremio Kerberos principal, and Dremio-only local credentials."
echo "Hive, PostgreSQL, RustFS, KDC, Spark, JupyterHub, and TPCH data/workspaces will be preserved."
read -r -p 'Type REMOVE DREMIO STATE to continue: ' confirmation
if [[ "${confirmation}" != "REMOVE DREMIO STATE" ]]; then
  echo "Dremio cleanup cancelled."
  exit 1
fi

compose_project="$(docker compose config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])')"
if [[ -z "${compose_project}" ]]; then
  echo "ERROR: Could not determine the current Compose project. No state was removed." >&2
  exit 1
fi

dremio_candidates="$(docker ps -aq \
  --filter 'label=com.docker.compose.service=dremio' \
  --filter "label=com.docker.compose.project=${compose_project}" \
  --filter "label=com.docker.compose.project.working_dir=${ROOT_DIR}")"
dremio_container_count="$(printf '%s\n' "${dremio_candidates}" | sed '/^$/d' | wc -l | tr -d ' ')"
if [[ "${dremio_container_count}" -gt 1 ]]; then
  echo "ERROR: Found multiple Dremio containers for ${ROOT_DIR}. No state was removed." >&2
  exit 1
fi
dremio_container="${dremio_candidates}"

volume_candidates="$(docker volume ls -q \
  --filter "label=com.docker.compose.project=${compose_project}" \
  --filter 'label=com.docker.compose.volume=dremio-data')"
volume_count="$(printf '%s\n' "${volume_candidates}" | sed '/^$/d' | wc -l | tr -d ' ')"
if [[ "${volume_count}" -gt 1 ]]; then
  echo "ERROR: Found multiple candidate Dremio volumes for ${compose_project}. No state was removed." >&2
  exit 1
fi
volume_name="${volume_candidates}"

if [[ -n "${dremio_container}" ]]; then
  mounted_volume="$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/opt/dremio/data"}}{{.Name}}{{end}}{{end}}' "${dremio_container}")"
  if [[ -z "${volume_name}" || "${mounted_volume}" != "${volume_name}" ]]; then
    echo "ERROR: Could not verify the Dremio container's data volume by mount and Compose labels. No state was removed." >&2
    exit 1
  fi
fi

kerberos_candidates="$(docker ps -aq \
  --filter 'label=com.docker.compose.service=kdc' \
  --filter "label=com.docker.compose.project=${compose_project}" \
  --filter "label=com.docker.compose.project.working_dir=${ROOT_DIR}")"
kerberos_container_count="$(printf '%s\n' "${kerberos_candidates}" | sed '/^$/d' | wc -l | tr -d ' ')"
if [[ "${kerberos_container_count}" -ne 1 ]]; then
  echo "ERROR: Expected exactly one KDC container for ${ROOT_DIR}; found ${kerberos_container_count}. No state was removed." >&2
  exit 1
fi
kdc_container="${kerberos_candidates}"
kdc_running="$(docker inspect --format '{{.State.Running}}' "${kdc_container}")"
if [[ "${kdc_running}" != "true" ]]; then
  echo "ERROR: The retained KDC container is not running. Start only the KDC, then rerun cleanup. No state was removed." >&2
  exit 1
fi

volume_users=""
if [[ -n "${volume_name}" ]]; then
  volume_users="$(docker ps -aq --filter "volume=${volume_name}")"
  if [[ -n "${dremio_container}" ]]; then
    if [[ "${volume_users}" != "${dremio_container}" ]]; then
      echo "ERROR: The Dremio volume is shared or has an unexpected container reference. No state was removed." >&2
      exit 1
    fi
  elif [[ -n "${volume_users}" ]]; then
    echo "ERROR: A container references the Dremio volume but is not the identified Dremio service. No state was removed." >&2
    exit 1
  fi
fi

realm_from_env=""
if [[ -f .env ]]; then
  realm_from_env="$(sed -n 's/^KERBEROS_REALM=//p' .env | tail -n 1)"
fi
realm="${KERBEROS_REALM:-${realm_from_env:-LAKEHOUSE.LOCAL}}"
principal="dremio@${realm}"
principal_info="$(docker exec "${kdc_container}" kadmin.local -r "${realm}" -q "getprinc ${principal}" 2>&1 || true)"
principal_exists=false
if [[ "${principal_info}" == *"Principal: ${principal}"* ]]; then
  principal_exists=true
elif [[ "${principal_info}" != *"Principal does not exist"* ]]; then
  echo "ERROR: Could not safely determine whether ${principal} exists in the KDC. No state was removed." >&2
  exit 1
fi

if [[ "${principal_exists}" == true ]]; then
  docker exec "${kdc_container}" kadmin.local -r "${realm}" -q "delete_principal -force ${principal}" >/dev/null
fi
if [[ -n "${dremio_container}" ]]; then
  docker rm -f "${dremio_container}" >/dev/null
fi
if [[ -n "${volume_name}" ]]; then
  docker volume rm "${volume_name}" >/dev/null
fi

rm -f -- \
  .runtime/credentials/dremio-admin-password \
  .runtime/credentials/dremio-writer-password \
  .runtime/credentials/dremio-user-a-password \
  .runtime/credentials/dremio-user-b-password \
  .runtime/credentials/keytabs/dremio.keytab

echo "Dremio-only local runtime state was cleaned. Retained data volumes and credentials were not changed."
