#!/usr/bin/env bash
set -euo pipefail

python /opt/airflow/scripts/validate-bundle-config.py

# Unit 2 passes host-visible paths to Docker Engine. Keep only non-secret source
# files and mode-0600 placeholders in the scheduler's path view; Docker Engine
# resolves the same paths against the real host project tree when it creates a
# Spark container. The writer credential contents are never mounted in Airflow.
if [[ "${1:-}" == "scheduler" ]]; then
  project_root="${LAKEHOUSE_PROJECT_ROOT:?LAKEHOUSE_PROJECT_ROOT is required}"
  credential_root="${project_root}/.runtime/credentials"
  mkdir -p "${credential_root}/keytabs"
  for relative_path in \
    keytabs/write-service-account.keytab \
    rustfs-writer-access-key \
    rustfs-writer-secret-key; do
    placeholder="${credential_root}/${relative_path}"
    if [[ ! -e "${placeholder}" ]]; then
      (umask 077; : > "${placeholder}")
    fi
    chmod 600 "${placeholder}"
  done
fi

exec /entrypoint "$@"
