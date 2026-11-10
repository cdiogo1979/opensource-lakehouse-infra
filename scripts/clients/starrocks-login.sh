#!/usr/bin/env bash
# Open a StarRocks SQL session with your username and password.
#
#   scripts/clients/starrocks-login.sh [--password-file FILE] <username> [mysql args...]
#
# StarRocks checks the password against the LDAP directory, the same password as
# for Keycloak sign-in. The MySQL 9.x client sends it with the cleartext plugin,
# so the connection must use TLS: the FE certificate is verified against the
# local StarRocks CA (the FE refuses plain-text connections anyway). The password
# is read without echo (or from FILE) and reaches the client container through
# its environment (MYSQL_PWD), never as an argument; it is never printed.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
CLIENT_IMAGE="mysql:9.7.2@sha256:e2fa358a74ac81148e7e27d9433e4c0ab62133de8ea4428b4f39a51a4ba7d07f"

usage() { echo "Usage: scripts/clients/starrocks-login.sh [--password-file FILE] <username> [mysql args...]" >&2; }

password_file=""
if [[ "${1:-}" == --password-file ]]; then
  password_file="${2:-}"
  shift 2 || { usage; exit 2; }
fi
username="${1:-}"
[[ -n "$username" ]] || { usage; exit 2; }
shift

if [[ -n "$password_file" ]]; then
  [[ -f "$password_file" && ! -L "$password_file" ]] || { echo "ERROR: password file is unavailable." >&2; exit 2; }
  password="$(head -n 1 "$password_file")"
else
  read -r -s -p "Password for ${username}: " password
  echo >&2
fi

tty_flags=(-i)
[[ -t 0 && -t 1 ]] && tty_flags=(-it)
MYSQL_PWD="$password" docker run --rm "${tty_flags[@]}" --network lakehouse-local_core \
  -e MYSQL_PWD \
  -v "$ROOT_DIR/.runtime/container-mounts/starrocks-ca.crt:/run/starrocks-ca.crt:ro" \
  --entrypoint mysql "$CLIENT_IMAGE" \
  -h starrocks-fe -P 9030 -u "$username" \
  --ssl-mode=VERIFY_IDENTITY --ssl-ca=/run/starrocks-ca.crt \
  --enable-cleartext-plugin \
  "$@"
