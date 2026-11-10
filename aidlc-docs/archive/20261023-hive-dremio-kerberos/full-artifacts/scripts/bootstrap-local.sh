#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CREDENTIAL_DIR="${ROOT_DIR}/.runtime/credentials"

if ! command -v openssl >/dev/null 2>&1; then
  echo "ERROR: openssl is required to generate local credentials." >&2
  exit 1
fi

mkdir -p "${CREDENTIAL_DIR}"
chmod 700 "${ROOT_DIR}/.runtime" "${CREDENTIAL_DIR}"
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

create_secret_file "postgres-password" 32
create_secret_file "rustfs-access-key" 24
create_secret_file "rustfs-secret-key" 40
create_secret_file "kdc-master-password" 32
if [[ ! -e "${CREDENTIAL_DIR}/dremio-admin-password" ]]; then
  { printf 'Aa1!'; openssl rand -hex 24; } > "${CREDENTIAL_DIR}/dremio-admin-password.tmp"
  chmod 600 "${CREDENTIAL_DIR}/dremio-admin-password.tmp"
  if ! mv -n "${CREDENTIAL_DIR}/dremio-admin-password.tmp" "${CREDENTIAL_DIR}/dremio-admin-password"; then
    rm -f "${CREDENTIAL_DIR}/dremio-admin-password.tmp"
  fi
fi
if [[ ! -s "${CREDENTIAL_DIR}/dremio-admin-password" ]]; then
  echo "ERROR: Required credential file is empty: dremio-admin-password" >&2
  exit 1
fi
chmod 600 "${CREDENTIAL_DIR}/dremio-admin-password"

if [[ ! -e "${CREDENTIAL_DIR}/dremio-writer-password" ]]; then
  { printf 'Aa1!'; openssl rand -hex 24; } > "${CREDENTIAL_DIR}/dremio-writer-password.tmp"
  chmod 600 "${CREDENTIAL_DIR}/dremio-writer-password.tmp"
  if ! mv -n "${CREDENTIAL_DIR}/dremio-writer-password.tmp" "${CREDENTIAL_DIR}/dremio-writer-password"; then
    rm -f "${CREDENTIAL_DIR}/dremio-writer-password.tmp"
  fi
fi
if [[ ! -s "${CREDENTIAL_DIR}/dremio-writer-password" ]]; then
  echo "ERROR: Required credential file is empty: dremio-writer-password" >&2
  exit 1
fi
chmod 600 "${CREDENTIAL_DIR}/dremio-writer-password"

create_dremio_user_password() {
  local identity="$1"
  local path="${CREDENTIAL_DIR}/dremio-${identity}-password"

  if [[ ! -e "${path}" ]]; then
    { printf 'Aa1!'; openssl rand -hex 24; } > "${path}.tmp"
    chmod 600 "${path}.tmp"
    if ! mv -n "${path}.tmp" "${path}"; then
      rm -f "${path}.tmp"
    fi
  fi

  if [[ ! -s "${path}" ]]; then
    echo "ERROR: Required credential file is empty: dremio-${identity}-password" >&2
    exit 1
  fi
  chmod 600 "${path}"
}

create_dremio_user_password "user-a"
create_dremio_user_password "user-b"

create_secret_file "rustfs-admin-secret-key" 40
create_secret_file "rustfs-writer-secret-key" 40
create_secret_file "rustfs-hive-secret-key" 40
create_secret_file "rustfs-user-a-secret-key" 40
create_secret_file "rustfs-user-b-secret-key" 40
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

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required to render the local Hive configuration." >&2
  exit 1
fi
python3 "${ROOT_DIR}/scripts/render-metastore-config.py"

echo "Local credential files are ready under .runtime/credentials/."
echo "Values are not displayed. Existing files were preserved."
