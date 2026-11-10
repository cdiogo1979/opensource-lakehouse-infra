#!/usr/bin/env bash
set -euo pipefail
umask 077

readonly root_password_file=/run/secrets/ranger-db-root-password
readonly app_user_password_file=/run/secrets/ranger-db-service-password
readonly app_user=rangeradmin

for secret in "$root_password_file" "$app_user_password_file"; do
  if [[ ! -s "$secret" || ! -r "$secret" ]]; then
    echo "Ranger test DB startup blocked: required secret file is missing." >&2
    exit 2
  fi
done

service_password="$(<"$app_user_password_file")"
if [[ ! "$service_password" =~ ^[a-f0-9]{64}$ ]]; then
  echo "Ranger test DB startup blocked: service secret has an invalid generated format." >&2
  exit 2
fi
unset service_password
export POSTGRES_PASSWORD_FILE="$root_password_file"
exec /usr/local/bin/docker-entrypoint.sh "$@"
