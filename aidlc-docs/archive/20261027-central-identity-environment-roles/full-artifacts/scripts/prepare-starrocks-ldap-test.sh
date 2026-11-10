#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly ROOT_DIR
readonly SECRET_DIR="${ROOT_DIR}/.runtime/starrocks-ldap-test/secrets"
readonly LDAP_SECRET_DIR="${ROOT_DIR}/.runtime/ranger-test/secrets"
readonly TEST_USER_PASSWORD_FILE="${LDAP_SECRET_DIR}/ranger-test-user-password"

if [[ ! -s "$TEST_USER_PASSWORD_FILE" ]]; then
  echo "Isolated FreeIPA test-user credential is unavailable; no files were prepared." >&2
  exit 2
fi
if [[ "$(stat -f '%Lp' "$TEST_USER_PASSWORD_FILE")" != 600 ]]; then
  echo "Isolated FreeIPA test-user credential must have mode 0600; no files were prepared." >&2
  exit 2
fi
if ! command -v docker >/dev/null 2>&1 || ! command -v openssl >/dev/null 2>&1; then
  echo "Docker and openssl are required; no files were prepared." >&2
  exit 2
fi

mkdir -p "$SECRET_DIR"
chmod 0700 "$ROOT_DIR/.runtime/starrocks-ldap-test" "$SECRET_DIR"

create_random_secret() {
  local path="$1"
  if [[ ! -e "$path" ]]; then
    openssl rand -hex 32 > "$path"
  fi
  if [[ -L "$path" || ! -f "$path" || "$(stat -f '%Lp' "$path")" != 600 ]]; then
    echo "A StarRocks LDAP test secret has an unsafe file type or mode; no changes applied." >&2
    exit 2
  fi
}

create_random_secret "$SECRET_DIR/keystore-password"
create_random_secret "$SECRET_DIR/mysql-root-password"

if [[ ! -e "$SECRET_DIR/starrocks-test.jks" ]]; then
  docker run --rm --network none \
    --volume "$SECRET_DIR:/test:rw" \
    --entrypoint /usr/bin/keytool local/starrocks-fe:4.1.6-kerberos \
    -genkeypair -noprompt \
    -alias starrocks-ldap-test \
    -keyalg RSA -keysize 2048 -validity 30 \
    -dname "CN=localhost,OU=Disposable Test,O=Lakehouse,C=PT" \
    -ext "SAN=dns:localhost,ip:127.0.0.1,dns:starrocks-ldap-test-fe" \
    -keystore /test/starrocks-test.jks -storetype JKS \
    -storepass:file /test/keystore-password \
    -keypass:file /test/keystore-password >/dev/null 2>&1
  chmod 0600 "$SECRET_DIR/starrocks-test.jks"
fi
if [[ ! -s "$SECRET_DIR/starrocks-test.crt" ]]; then
  docker run --rm --network none \
    --volume "$SECRET_DIR:/test:rw" \
    --entrypoint /usr/bin/keytool local/starrocks-fe:4.1.6-kerberos \
    -exportcert -rfc -alias starrocks-ldap-test \
    -keystore /test/starrocks-test.jks \
    -storepass:file /test/keystore-password \
    -file /test/starrocks-test.crt >/dev/null 2>&1
  chmod 0600 "$SECRET_DIR/starrocks-test.crt"
fi

write_client_file() {
  local path="$1" user="$2" password_source="$3"
  {
    printf '[client]\nuser=%s\npassword=' "$user"
    tr -d '\r\n' < "$password_source"
    printf '\nhost=127.0.0.1\nport=9030\nprotocol=TCP\nssl-mode=VERIFY_CA\nssl-ca=/run/sql-tls/starrocks-test.crt\n'
  } > "$path"
  chmod 0600 "$path"
}

write_client_file "$SECRET_DIR/mysql-admin.cnf" root "$SECRET_DIR/mysql-root-password"
write_client_file "$SECRET_DIR/developer-user.cnf" developer-user "$TEST_USER_PASSWORD_FILE"
write_client_file "$SECRET_DIR/analyst-user.cnf" analyst-user "$TEST_USER_PASSWORD_FILE"
write_client_file "$SECRET_DIR/write-service-account.cnf" write-service-account "$TEST_USER_PASSWORD_FILE"

find "$SECRET_DIR" -type f -exec chmod 0600 {} +
echo "Prepared private StarRocks LDAP test TLS and client files. Secret values were not displayed."
