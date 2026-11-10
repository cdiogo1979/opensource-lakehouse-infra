#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CREDENTIAL_DIR="${ROOT_DIR}/.runtime/credentials"
TEST_CREDENTIAL_DIR="${ROOT_DIR}/.runtime/identity-provisioning/test-credentials"

if ! command -v openssl >/dev/null 2>&1; then
  echo "ERROR: openssl is required to generate local credentials." >&2
  exit 1
fi

mkdir -p "${CREDENTIAL_DIR}"
mkdir -p "${TEST_CREDENTIAL_DIR}"
chmod 700 "${ROOT_DIR}/.runtime" "${CREDENTIAL_DIR}"
chmod 700 "${ROOT_DIR}/.runtime/identity-provisioning" "${TEST_CREDENTIAL_DIR}"
umask 077

create_secret_file() {
  local name="$1"
  local bytes="$2"
  local path="${CREDENTIAL_DIR}/${name}"

  if [[ ! -e "${path}" ]]; then
    openssl rand -hex "${bytes}" > "${path}.tmp"
    chmod 600 "${path}.tmp"
    if ! mv -n "${path}.tmp" "${path}"; then
      rm -f "${path}.tmp"
    fi
  fi

  if [[ ! -s "${path}" ]]; then
    echo "ERROR: Required credential file is empty: ${path}" >&2
    exit 1
  fi
  chmod 600 "${path}"
}

create_test_secret_file() {
  local name="$1"
  local bytes="$2"
  local path="${TEST_CREDENTIAL_DIR}/${name}"

  if [[ ! -e "${path}" ]]; then
    openssl rand -hex "${bytes}" > "${path}.tmp"
    chmod 600 "${path}.tmp"
    if ! mv -n "${path}.tmp" "${path}"; then
      rm -f "${path}.tmp"
    fi
  fi

  if [[ ! -s "${path}" ]]; then
    echo "ERROR: Required test credential file is empty: ${path}" >&2
    exit 1
  fi
  chmod 600 "${path}"
}

create_secret_file "postgres-password" 32
create_secret_file "rustfs-access-key" 24
create_secret_file "rustfs-secret-key" 40
create_secret_file "kdc-master-password" 32
create_secret_file "freeipa-admin-password" 32
create_secret_file "freeipa-directory-manager-password" 32
create_secret_file "freeipa-jupyterhub-ldap-reader-password" 40

AUTH_STATE_KEY="${CREDENTIAL_DIR}/jupyterhub-auth-state-crypt-key"
if [[ ! -e "${AUTH_STATE_KEY}" ]]; then
  python3 -c 'import base64, secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())' > "${AUTH_STATE_KEY}.tmp"
  chmod 600 "${AUTH_STATE_KEY}.tmp"
  if ! mv -n "${AUTH_STATE_KEY}.tmp" "${AUTH_STATE_KEY}"; then
    rm -f "${AUTH_STATE_KEY}.tmp"
  fi
fi
if [[ ! -s "${AUTH_STATE_KEY}" ]]; then
  echo "ERROR: Required credential file is empty: ${AUTH_STATE_KEY}" >&2
  exit 1
fi
chmod 600 "${AUTH_STATE_KEY}"

create_secret_file "rustfs-admin-secret-key" 40
create_secret_file "rustfs-writer-secret-key" 40
create_secret_file "rustfs-developer-secret-key" 40
create_secret_file "rustfs-analyst-secret-key" 40
create_test_secret_file "rustfs-root-secret-key" 40
create_test_secret_file "rustfs-admin-secret-key" 40
create_test_secret_file "rustfs-writer-secret-key" 40
create_test_secret_file "rustfs-developer-secret-key" 40
create_test_secret_file "rustfs-analyst-secret-key" 40
create_test_secret_file "freeipa-rustfs-reader-password" 40
if [[ ! -s "${TEST_CREDENTIAL_DIR}/rustfs-root-access-key" ]]; then
  printf 'identity-test-root\n' > "${TEST_CREDENTIAL_DIR}/rustfs-root-access-key"
fi
chmod 600 "${TEST_CREDENTIAL_DIR}/rustfs-root-access-key"
RUSTFS_TEST_ENV="${TEST_CREDENTIAL_DIR}/rustfs.env"
if [[ ! -s "${RUSTFS_TEST_ENV}" ]]; then
  {
    printf 'RUSTFS_ACCESS_KEY=%s\n' "$(cat "${TEST_CREDENTIAL_DIR}/rustfs-root-access-key")"
    printf 'RUSTFS_SECRET_KEY=%s\n' "$(cat "${TEST_CREDENTIAL_DIR}/rustfs-root-secret-key")"
  } > "${RUSTFS_TEST_ENV}"
fi
chmod 600 "${RUSTFS_TEST_ENV}"
create_secret_file "rustfs-hive-secret-key" 40
create_secret_file "rustfs-user-a-secret-key" 40
create_secret_file "rustfs-user-b-secret-key" 40
create_secret_file "rustfs-starrocks-secret-key" 40
create_secret_file "postgres-admin-password" 32

# RustFS identifies IAM users by access key, so the stable account names are
# their S3 access-key IDs. Only the corresponding secret keys are random.
write_rustfs_identity_id() {
  local name="$1"
  local identity="$2"
  printf '%s\n' "${identity}" > "${CREDENTIAL_DIR}/${name}"
  chmod 600 "${CREDENTIAL_DIR}/${name}"
}
write_rustfs_identity_id "rustfs-admin-access-key" "admin"
write_rustfs_identity_id "rustfs-writer-access-key" "write-service-account"
write_rustfs_identity_id "rustfs-hive-access-key" "hive-metastore"
write_rustfs_identity_id "rustfs-user-a-access-key" "user_a"
write_rustfs_identity_id "rustfs-user-b-access-key" "user_b"
write_rustfs_identity_id "rustfs-developer-access-key" "developer-user"
write_rustfs_identity_id "rustfs-analyst-access-key" "analyst-user"

# Jupyter single-user containers receive only their own individual credential
# files and the host primary group. Keep both parent directories owner-only.
for name in \
  rustfs-admin-access-key rustfs-admin-secret-key \
  rustfs-user-a-access-key rustfs-user-a-secret-key \
  rustfs-user-b-access-key rustfs-user-b-secret-key; do
  if [[ ! -s "${CREDENTIAL_DIR}/${name}" ]]; then
    echo "ERROR: Required Jupyter RustFS identity file is empty: ${name}" >&2
    exit 1
  fi
  chmod 640 "${CREDENTIAL_DIR}/${name}"
done

KEYTAB_DIR="${CREDENTIAL_DIR}/keytabs"
mkdir -p "${KEYTAB_DIR}"
chmod 700 "${KEYTAB_DIR}"

PROVISIONER_STATUS_DIR="${ROOT_DIR}/.runtime/identity-provisioning"
mkdir -p "${PROVISIONER_STATUS_DIR}"
chmod 700 "${PROVISIONER_STATUS_DIR}"

RUSTFS_ENV="${CREDENTIAL_DIR}/rustfs.env"
if [[ ! -e "${RUSTFS_ENV}" ]]; then
  {
    printf 'RUSTFS_ACCESS_KEY=%s\n' "$(cat "${CREDENTIAL_DIR}/rustfs-access-key")"
    printf 'RUSTFS_SECRET_KEY=%s\n' "$(cat "${CREDENTIAL_DIR}/rustfs-secret-key")"
    printf 'AWS_ACCESS_KEY_ID=%s\n' "$(cat "${CREDENTIAL_DIR}/rustfs-access-key")"
    printf 'AWS_SECRET_ACCESS_KEY=%s\n' "$(cat "${CREDENTIAL_DIR}/rustfs-secret-key")"
  } > "${RUSTFS_ENV}.tmp"
  chmod 600 "${RUSTFS_ENV}.tmp"
  if ! mv -n "${RUSTFS_ENV}.tmp" "${RUSTFS_ENV}"; then
    rm -f "${RUSTFS_ENV}.tmp"
  fi
fi
if [[ ! -s "${RUSTFS_ENV}" ]]; then
  echo "ERROR: Required RustFS runtime environment file is empty." >&2
  exit 1
fi
chmod 600 "${RUSTFS_ENV}"

WRITER_RUSTFS_ENV="${CREDENTIAL_DIR}/rustfs-writer.env"
{
  printf 'AWS_ACCESS_KEY_ID=%s\n' "$(cat "${CREDENTIAL_DIR}/rustfs-writer-access-key")"
  printf 'AWS_SECRET_ACCESS_KEY=%s\n' "$(cat "${CREDENTIAL_DIR}/rustfs-writer-secret-key")"
} > "${WRITER_RUSTFS_ENV}.tmp"
chmod 600 "${WRITER_RUSTFS_ENV}.tmp"
mv -f "${WRITER_RUSTFS_ENV}.tmp" "${WRITER_RUSTFS_ENV}"
if [[ ! -s "${WRITER_RUSTFS_ENV}" ]]; then
  echo "ERROR: Required RustFS writer credential environment file is empty." >&2
  exit 1
fi
chmod 600 "${WRITER_RUSTFS_ENV}"

# The upstream FreeIPA container reads unattended installer options from
# /data/ipa-server-install-options on first initialization. Compose mounts this
# owner-only local file read-only under /run/secrets; the FreeIPA entrypoint
# creates a symlink in its named data volume, so secret contents are not copied
# into persistent state. Keep passwords in this ignored directory and never
# print the options file.
FREEIPA_OPTIONS="${CREDENTIAL_DIR}/freeipa-server-install-options"
read_local_setting() {
  local variable_name="$1"
  local default_value="$2"
  local environment_value="${!variable_name:-}"
  if [[ -n "${environment_value}" ]]; then
    printf '%s' "${environment_value}"
  elif [[ -f "${ROOT_DIR}/.env" ]]; then
    local file_value
    file_value="$(sed -n "s/^${variable_name}=//p" "${ROOT_DIR}/.env" | tail -n 1)"
    if [[ -n "${file_value}" ]]; then
      printf '%s' "${file_value}"
    else
      printf '%s' "${default_value}"
    fi
  else
    printf '%s' "${default_value}"
  fi
}
FREEIPA_HOSTNAME="$(read_local_setting FREEIPA_HOSTNAME ipa.lakehouse.local)"
FREEIPA_VALIDATION_IP="$(read_local_setting FREEIPA_VALIDATION_IP 172.30.250.10)"
FREEIPA_REALM="$(read_local_setting KERBEROS_REALM LAKEHOUSE.LOCAL)"
FREEIPA_DOMAIN="$(printf '%s' "${FREEIPA_REALM}" | tr '[:upper:]' '[:lower:]')"
FREEIPA_DOMAIN="$(read_local_setting FREEIPA_DOMAIN "${FREEIPA_DOMAIN}")"
FREEIPA_DNS_FORWARDER="$(read_local_setting FREEIPA_DNS_FORWARDER 1.1.1.1)"
if [[ ! "${FREEIPA_HOSTNAME}" =~ ^[A-Za-z0-9.-]+$ || ! "${FREEIPA_DOMAIN}" =~ ^[A-Za-z0-9.-]+$ || ! "${FREEIPA_REALM}" =~ ^[A-Za-z0-9.-]+$ ]]; then
  echo "ERROR: FreeIPA hostname, domain, or realm contains unsupported characters." >&2
  exit 1
fi
if ! python3 -c 'import ipaddress,sys; ipaddress.ip_address(sys.argv[1])' "${FREEIPA_VALIDATION_IP}" >/dev/null 2>&1; then
  echo "ERROR: FREEIPA_VALIDATION_IP is not a valid IP address." >&2
  exit 1
fi
if ! python3 -c 'import ipaddress,sys; ipaddress.ip_address(sys.argv[1])' "${FREEIPA_DNS_FORWARDER}" >/dev/null 2>&1; then
  echo "ERROR: FREEIPA_DNS_FORWARDER is not a valid IP address." >&2
  exit 1
fi
if [[ ! -e "${FREEIPA_OPTIONS}" ]]; then
  {
    printf '%s\n' "--unattended"
    printf '%s\n' "--realm=${FREEIPA_REALM}"
    printf '%s\n' "--domain=${FREEIPA_DOMAIN}"
    printf '%s\n' "--hostname=${FREEIPA_HOSTNAME}"
    printf '%s\n' "--ip-address=${FREEIPA_VALIDATION_IP}"
    printf '%s\n' "--ds-password=$(cat "${CREDENTIAL_DIR}/freeipa-directory-manager-password")"
    printf '%s\n' "--admin-password=$(cat "${CREDENTIAL_DIR}/freeipa-admin-password")"
    printf '%s\n' "--setup-dns"
    printf '%s\n' "--forwarder=${FREEIPA_DNS_FORWARDER}"
    printf '%s\n' "--no-ntp"
    printf '%s\n' "--skip-mem-check"
  } > "${FREEIPA_OPTIONS}.tmp"
  chmod 600 "${FREEIPA_OPTIONS}.tmp"
  if ! mv -n "${FREEIPA_OPTIONS}.tmp" "${FREEIPA_OPTIONS}"; then
    rm -f "${FREEIPA_OPTIONS}.tmp"
  fi
fi
python3 - "${FREEIPA_OPTIONS}" "${FREEIPA_DNS_FORWARDER}" <<'PY'
from pathlib import Path
import os
import sys
import tempfile

options_path = Path(sys.argv[1])
forwarder = sys.argv[2]
lines = options_path.read_text().splitlines()
updated = [line for line in lines if not line.startswith("--forwarder=")]
updated.append(f"--forwarder={forwarder}")
if updated != lines:
    fd, temp_name = tempfile.mkstemp(dir=options_path.parent, prefix="freeipa-options.")
    try:
        with os.fdopen(fd, "w") as options_file:
            os.chmod(temp_name, 0o600)
            options_file.write("\n".join(updated) + "\n")
        os.replace(temp_name, options_path)
        os.chmod(options_path, 0o600)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
PY
if ! grep -Fxq -- "--skip-mem-check" "${FREEIPA_OPTIONS}"; then
  printf '%s\n' "--skip-mem-check" >> "${FREEIPA_OPTIONS}"
  chmod 600 "${FREEIPA_OPTIONS}"
fi
if [[ -e "${FREEIPA_OPTIONS}.tmp" ]]; then
  rm -f "${FREEIPA_OPTIONS}.tmp"
fi
if [[ ! -s "${FREEIPA_OPTIONS}" ]]; then
  echo "ERROR: Required FreeIPA installer options file is empty." >&2
  exit 1
fi
chmod 600 "${FREEIPA_OPTIONS}"
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required to render the local Hive configuration." >&2
  exit 1
fi
python3 "${ROOT_DIR}/scripts/render-metastore-config.py"

echo "Local credential files are ready under .runtime/credentials/."
echo "Values are not displayed. Existing files were preserved."
