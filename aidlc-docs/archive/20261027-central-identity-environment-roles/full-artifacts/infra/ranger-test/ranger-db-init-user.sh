#!/usr/bin/env bash
set -euo pipefail
umask 077

readonly password_file=/run/secrets/ranger-db-service-password
readonly app_user=rangeradmin
readonly app_database=ranger

if [[ ! -s "$password_file" || ! -r "$password_file" ]]; then
  echo "Ranger test DB initialization blocked: service secret is missing." >&2
  exit 2
fi

service_password="$(<"$password_file")"
if [[ ! "$service_password" =~ ^[a-f0-9]{64}$ ]]; then
  echo "Ranger test DB initialization blocked: service secret has an invalid generated format." >&2
  exit 2
fi

psql --set=ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
CREATE USER ${app_user} WITH PASSWORD '${service_password}';
CREATE DATABASE ${app_database};
GRANT ALL PRIVILEGES ON DATABASE ${app_database} TO ${app_user};
SQL
unset service_password
