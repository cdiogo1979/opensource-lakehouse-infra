#!/usr/bin/env bash
set -euo pipefail

password_file=/run/secrets/keycloak_admin_password
if [[ ! -r "$password_file" ]]; then
  echo "Keycloak bootstrap administrator credential file is unavailable." >&2
  exit 1
fi
IFS= read -r KC_BOOTSTRAP_ADMIN_PASSWORD < "$password_file" || true
if [[ -z "${KC_BOOTSTRAP_ADMIN_PASSWORD:-}" ]]; then
  echo "Keycloak bootstrap administrator credential file is empty." >&2
  exit 1
fi
export KC_BOOTSTRAP_ADMIN_PASSWORD
export KC_BOOTSTRAP_ADMIN_USERNAME=admin
exec /opt/keycloak/bin/kc.sh "$@"
