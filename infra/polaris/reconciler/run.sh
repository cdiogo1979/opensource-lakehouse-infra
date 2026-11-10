#!/bin/sh
set -u

interval="${RECONCILE_INTERVAL_SECONDS:-300}"
case "$interval" in
  ''|*[!0-9]*) echo "RECONCILE_INTERVAL_SECONDS must be a positive integer" >&2; exit 2 ;;
esac
if [ "$interval" -lt 1 ]; then
  echo "RECONCILE_INTERVAL_SECONDS must be a positive integer" >&2
  exit 2
fi

while :; do
  echo "Starting Keycloak-to-Polaris group reconciliation"
  if python /opt/lakehouse/polaris/reconcile-keycloak-groups.py \
    --keycloak-admin-password-file /run/secrets/keycloak_admin_password \
    --polaris-credential-file /run/secrets/polaris_bootstrap_credentials \
    --keycloak-url "${KEYCLOAK_URL:-http://keycloak:8080}" \
    --polaris-url "${POLARIS_URL:-http://polaris:8181}"; then
    echo "Group reconciliation succeeded; next run in ${interval}s"
  else
    echo "Group reconciliation failed; retrying in ${interval}s" >&2
  fi
  if [ "${STARROCKS_ENABLED:-true}" != "false" ]; then
    if python /opt/lakehouse/starrocks/reconcile-starrocks-users.py \
      --transport network \
      --keycloak-url "${KEYCLOAK_URL:-http://keycloak:8080}" \
      --keycloak-admin-password-file /run/secrets/keycloak_admin_password \
      --root-password-file /run/secrets/starrocks_root_password; then
      echo "StarRocks user reconciliation succeeded"
    else
      echo "StarRocks user reconciliation failed; retrying in ${interval}s" >&2
    fi
  fi
  sleep "$interval"
done
