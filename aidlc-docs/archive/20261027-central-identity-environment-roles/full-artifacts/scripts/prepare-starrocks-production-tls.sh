#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TLS_DIR="${ROOT_DIR}/.runtime/starrocks-production/sql-tls"
IMAGE="local/starrocks-fe:4.1.6-kerberos"
mkdir -p "${TLS_DIR}"
chmod 700 "${ROOT_DIR}/.runtime" "${ROOT_DIR}/.runtime/starrocks-production" "${TLS_DIR}"

if ! command -v openssl >/dev/null 2>&1 || ! command -v docker >/dev/null 2>&1; then
  echo "OpenSSL and Docker are required; SQL TLS files were not prepared." >&2
  exit 2
fi
if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
  echo "The pinned local StarRocks FE image is unavailable; SQL TLS files were not prepared." >&2
  exit 2
fi

password_file="${TLS_DIR}/keystore-password"
keystore="${TLS_DIR}/starrocks-production.jks"
certificate="${TLS_DIR}/starrocks-production.crt"
for path in "${password_file}" "${keystore}" "${certificate}"; do
  if [[ -L "${path}" || ( -e "${path}" && ! -f "${path}" ) ]]; then
    echo "Unsafe SQL TLS file type detected; no TLS files were changed." >&2
    exit 2
  fi
done
if [[ ! -e "${password_file}" ]]; then
  openssl rand -hex 32 > "${password_file}.tmp"
  chmod 600 "${password_file}.tmp"
  if ! mv -n "${password_file}.tmp" "${password_file}"; then
    rm -f "${password_file}.tmp"
  fi
fi
if [[ ! -s "${password_file}" || "$(stat -f '%Lp' "${password_file}")" != 600 ]]; then
  echo "The StarRocks SQL keystore password must be a non-empty mode-0600 file." >&2
  exit 2
fi

if [[ ! -e "${keystore}" ]]; then
  docker run --rm --network none \
    --volume "${TLS_DIR}:/tls:rw" \
    --entrypoint /usr/bin/keytool "${IMAGE}" \
    -genkeypair -noprompt \
    -alias starrocks-production \
    -keyalg RSA -keysize 3072 -validity 3650 \
    -dname "CN=starrocks-fe,OU=Lakehouse,O=Lakehouse,C=PT" \
    -ext "SAN=dns:starrocks-fe,dns:localhost,ip:127.0.0.1" \
    -keystore /tls/starrocks-production.jks -storetype JKS \
    -storepass:file /tls/keystore-password \
    -keypass:file /tls/keystore-password >/dev/null 2>&1
  chmod 600 "${keystore}"
fi
if [[ ! -s "${keystore}" || "$(stat -f '%Lp' "${keystore}")" != 600 ]]; then
  echo "The StarRocks SQL keystore must be a non-empty mode-0600 file." >&2
  exit 2
fi
if [[ ! -e "${certificate}" ]]; then
  docker run --rm --network none \
    --volume "${TLS_DIR}:/tls:rw" \
    --entrypoint /usr/bin/keytool "${IMAGE}" \
    -exportcert -rfc -alias starrocks-production \
    -keystore /tls/starrocks-production.jks \
    -storepass:file /tls/keystore-password \
    -file /tls/starrocks-production.crt >/dev/null 2>&1
  chmod 644 "${certificate}"
fi
if [[ ! -s "${certificate}" ]] || ! openssl x509 -in "${certificate}" -noout >/dev/null 2>&1; then
  echo "The StarRocks SQL server certificate is unavailable or invalid." >&2
  exit 2
fi
echo "Prepared StarRocks SQL TLS server files. The certificate is self-signed; distribute its public certificate to SQL clients as their CA. Secret values were not displayed."
