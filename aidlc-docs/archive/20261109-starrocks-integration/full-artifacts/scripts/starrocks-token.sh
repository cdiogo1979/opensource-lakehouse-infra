#!/usr/bin/env bash
# Write a StarRocks login token for JDBC clients such as DBeaver.
#
#   scripts/starrocks-token.sh [--password-file FILE] [--watch] <username> <token-file>
#
# Gets a Keycloak access token from the `starrocks` client (password grant) and
# writes it to <token-file> (mode 0600) for Connector/J's `idTokenFile`. Tokens
# last five minutes and StarRocks checks them only when a connection opens, so
# --watch keeps the file fresh with the refresh token until the Keycloak session
# ends. The password is read without echo (or from FILE) and sent on stdin; no
# password or token is printed.
set -euo pipefail

KEYCLOAK_TOKEN_URL="http://127.0.0.1:${KEYCLOAK_HOST_PORT:-8080}/realms/lakehouse/protocol/openid-connect/token"

usage() { echo "Usage: scripts/starrocks-token.sh [--password-file FILE] [--watch] <username> <token-file>" >&2; }

password_file="" watch=false
while [[ "${1:-}" == --* ]]; do
  case "$1" in
    --password-file) password_file="${2:-}"; shift 2 || { usage; exit 2; } ;;
    --watch) watch=true; shift ;;
    *) usage; exit 2 ;;
  esac
done
username="${1:-}" token_file="${2:-}"
[[ -n "$username" && -n "$token_file" ]] || { usage; exit 2; }
[[ ! -L "$token_file" ]] || { echo "ERROR: refusing to write through a symlink: $token_file" >&2; exit 2; }
mkdir -p "$(dirname "$token_file")"

workdir="$(mktemp -d)"
chmod 700 "$workdir"
trap 'rm -rf "$workdir"' EXIT
umask 077

# Reads a token response on stdin; writes the access token atomically and echoes
# "<refresh token> <seconds until expiry>" for the caller.
store() {
  python3 -c '
import json, os, sys
body = json.load(sys.stdin)
path, temporary = sys.argv[1], sys.argv[1] + ".tmp"
with open(temporary, "w") as stream:
    stream.write(body["access_token"])
os.chmod(temporary, 0o600)
os.replace(temporary, path)
print(body.get("refresh_token", ""), int(body.get("expires_in", 300)))
' "$token_file"
}

if [[ -n "$password_file" ]]; then
  [[ -f "$password_file" && ! -L "$password_file" ]] || { echo "ERROR: password file is unavailable." >&2; exit 2; }
  password="$(head -n 1 "$password_file")"
else
  read -r -s -p "Keycloak password for ${username}: " password
  echo >&2
fi
if ! printf '%s' "$password" | curl -sS --fail -X POST "$KEYCLOAK_TOKEN_URL" \
    -d grant_type=password -d client_id=starrocks -d scope=openid \
    --data-urlencode "username=${username}" --data-urlencode "password@-" \
    -o "$workdir/response.json" 2>/dev/null; then
  unset password
  echo "ERROR: Keycloak did not issue a StarRocks token for ${username} (check the username and password)." >&2
  exit 1
fi
unset password
read -r refresh expires < <(store < "$workdir/response.json")
rm -f "$workdir/response.json"
echo "StarRocks token for ${username} written to ${token_file} (valid ${expires}s)."
[[ "$watch" == true ]] || exit 0

echo "Refreshing ${token_file} before each expiry; press Ctrl-C to stop."
while true; do
  sleep $(( expires > 90 ? expires - 60 : 30 ))
  if ! printf '%s' "$refresh" | curl -sS --fail -X POST "$KEYCLOAK_TOKEN_URL" \
      -d grant_type=refresh_token -d client_id=starrocks --data-urlencode "refresh_token@-" \
      -o "$workdir/response.json" 2>/dev/null; then
    echo "ERROR: the Keycloak session ended; rerun this command to sign in again." >&2
    exit 1
  fi
  read -r refresh expires < <(store < "$workdir/response.json")
  rm -f "$workdir/response.json"
  echo "Token refreshed ($(date '+%H:%M:%S'); valid ${expires}s)."
done
