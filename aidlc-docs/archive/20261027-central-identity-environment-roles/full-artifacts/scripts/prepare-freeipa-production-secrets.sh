#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CREDENTIAL_DIR="${ROOT_DIR}/.runtime/credentials"
mkdir -p "${CREDENTIAL_DIR}"
chmod 700 "${ROOT_DIR}/.runtime" "${CREDENTIAL_DIR}"

if ! command -v openssl >/dev/null 2>&1; then
  echo "OpenSSL is required; no production secret files were prepared." >&2
  exit 2
fi

create_secret() {
  local name="$1"
  local file="${CREDENTIAL_DIR}/${name}"
  if [[ -L "${file}" || ( -e "${file}" && ! -f "${file}" ) ]]; then
    echo "Unsafe file type for ${name}; no production secrets were changed." >&2
    exit 2
  fi
  if [[ ! -e "${file}" ]]; then
    openssl rand -hex 32 > "${file}.tmp"
    chmod 600 "${file}.tmp"
    if ! mv -n "${file}.tmp" "${file}"; then
      rm -f "${file}.tmp"
    fi
  fi
  if [[ ! -s "${file}" || "$(stat -f '%Lp' "${file}")" != 600 ]]; then
    echo "${name} must exist, be non-empty, and have mode 0600." >&2
    exit 2
  fi
}

create_secret freeipa-production-admin-password
create_secret freeipa-production-directory-manager-password
create_secret freeipa-production-starrocks-reader-password
create_secret freeipa-production-writer-password

options="${CREDENTIAL_DIR}/freeipa-production-server-install-options"
if [[ ! -e "${options}" ]]; then
  realm="${KERBEROS_REALM:-LAKEHOUSE.LOCAL}"
  domain="${FREEIPA_DOMAIN:-lakehouse.local}"
  hostname="${FREEIPA_PRODUCTION_HOSTNAME:-ipa-prod.lakehouse.local}"
  server_ip="${FREEIPA_PRODUCTION_IP:-172.31.250.10}"
  if [[ ! "${realm}" =~ ^[A-Z0-9.-]+$ || ! "${domain}" =~ ^[a-z0-9.-]+$ || ! "${hostname}" =~ ^[a-z0-9.-]+$ ]]; then
    echo "Production FreeIPA realm/domain/hostname has an unsupported format." >&2
    exit 2
  fi
  if ! python3 -c 'import ipaddress,sys; ipaddress.ip_address(sys.argv[1])' "${server_ip}" >/dev/null 2>&1; then
    echo "FREEIPA_PRODUCTION_IP is not a valid IP address." >&2
    exit 2
  fi
  {
    printf '%s\n' "--unattended"
    printf '%s\n' "--realm=${realm}"
    printf '%s\n' "--domain=${domain}"
    printf '%s\n' "--hostname=${hostname}"
    printf '%s\n' "--ip-address=${server_ip}"
    printf '%s\n' "--ds-password=$(tr -d '\r\n' < "${CREDENTIAL_DIR}/freeipa-production-directory-manager-password")"
    printf '%s\n' "--admin-password=$(tr -d '\r\n' < "${CREDENTIAL_DIR}/freeipa-production-admin-password")"
    printf '%s\n' "--no-ntp"
    printf '%s\n' "--skip-mem-check"
  } > "${options}.tmp"
  chmod 600 "${options}.tmp"
  if ! mv -n "${options}.tmp" "${options}"; then
    rm -f "${options}.tmp"
  fi
fi
if [[ -L "${options}" || ! -s "${options}" || "$(stat -f '%Lp' "${options}")" != 600 ]]; then
  echo "Production FreeIPA installer options must be a regular non-empty file with mode 0600." >&2
  exit 2
fi

echo "Prepared protected production FreeIPA credentials and installer options; values were not displayed."
