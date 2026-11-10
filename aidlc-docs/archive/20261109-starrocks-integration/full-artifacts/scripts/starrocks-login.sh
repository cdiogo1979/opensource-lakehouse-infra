#!/usr/bin/env bash
# Open a StarRocks SQL session as a Keycloak user.
#
#   scripts/starrocks-login.sh [--password-file FILE] <username> [mysql args...]
#
# Gets an access token from the Keycloak `starrocks` client (password grant) and
# logs in with the MySQL 9.x OpenID Connect client plugin over TLS, verifying the
# FE certificate against the local StarRocks CA (the plugin refuses plaintext).
# The password is read without echo (or from FILE) and sent to Keycloak on stdin;
# the token is kept in a private temporary file that is removed on exit. Neither
# is ever printed.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
CLIENT_IMAGE="mysql:9.7.2@sha256:e2fa358a74ac81148e7e27d9433e4c0ab62133de8ea4428b4f39a51a4ba7d07f"
KEYCLOAK_TOKEN_URL="http://127.0.0.1:${KEYCLOAK_HOST_PORT:-8080}/realms/lakehouse/protocol/openid-connect/token"

usage() { echo "Usage: scripts/starrocks-login.sh [--password-file FILE] <username> [mysql args...]" >&2; }

password_file=""
if [[ "${1:-}" == --password-file ]]; then
  password_file="${2:-}"
  shift 2 || { usage; exit 2; }
fi
username="${1:-}"
[[ -n "$username" ]] || { usage; exit 2; }
shift

workdir="$(mktemp -d)"
chmod 700 "$workdir"
trap 'rm -rf "$workdir"' EXIT

if [[ -n "$password_file" ]]; then
  [[ -f "$password_file" && ! -L "$password_file" ]] || { echo "ERROR: password file is unavailable." >&2; exit 2; }
  password="$(head -n 1 "$password_file")"
else
  read -r -s -p "Keycloak password for ${username}: " password
  echo >&2
fi

umask 077
if ! printf '%s' "$password" | curl -sS --fail -X POST "$KEYCLOAK_TOKEN_URL" \
    -d grant_type=password -d client_id=starrocks -d scope=openid \
    --data-urlencode "username=${username}" --data-urlencode "password@-" \
    -o "$workdir/response.json" 2>/dev/null; then
  unset password
  echo "ERROR: Keycloak did not issue a StarRocks token for ${username} (check the username and password)." >&2
  exit 1
fi
unset password
python3 -c 'import json,sys; sys.stdout.write(json.load(open(sys.argv[1]))["access_token"])' \
  "$workdir/response.json" > "$workdir/token"
rm -f "$workdir/response.json"

tty_flags=(-i)
[[ -t 0 && -t 1 ]] && tty_flags=(-it)
docker run --rm "${tty_flags[@]}" --network lakehouse-local_core \
  -v "$workdir/token:/run/starrocks-token:ro" \
  -v "$ROOT_DIR/.runtime/container-mounts/starrocks-ca.crt:/run/starrocks-ca.crt:ro" \
  --entrypoint mysql "$CLIENT_IMAGE" \
  -h starrocks-fe -P 9030 -u "$username" \
  --ssl-mode=VERIFY_IDENTITY --ssl-ca=/run/starrocks-ca.crt \
  --default-auth=authentication_openid_connect_client \
  --authentication-openid-connect-client-id-token-file=/run/starrocks-token \
  "$@"
