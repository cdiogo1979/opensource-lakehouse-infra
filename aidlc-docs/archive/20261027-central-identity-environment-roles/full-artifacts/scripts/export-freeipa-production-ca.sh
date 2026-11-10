#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CA_DIR="${ROOT_DIR}/.runtime/freeipa-production"
CA_FILE="${CA_DIR}/ca.crt"
TMP_FILE="${CA_FILE}.tmp"

mkdir -p "${CA_DIR}"
chmod 700 "${ROOT_DIR}/.runtime" "${CA_DIR}"
rm -f "${TMP_FILE}"
if ! docker cp iceberg-poc-freeipa-production:/etc/ipa/ca.crt "${TMP_FILE}" >/dev/null 2>&1; then
  echo "Unable to export the production FreeIPA CA; confirm the dedicated production service is installed." >&2
  exit 2
fi
if ! openssl x509 -in "${TMP_FILE}" -noout >/dev/null 2>&1; then
  rm -f "${TMP_FILE}"
  echo "The production FreeIPA CA export is not a valid X.509 certificate." >&2
  exit 2
fi
chmod 644 "${TMP_FILE}"
if [[ -e "${CA_FILE}" ]]; then
  if cmp -s "${CA_FILE}" "${TMP_FILE}"; then
    rm -f "${TMP_FILE}"
    echo "Production FreeIPA public CA certificate is already current."
    exit 0
  fi
  rm -f "${TMP_FILE}"
  echo "A different production FreeIPA CA is already present; review it before replacement." >&2
  exit 2
fi
mv "${TMP_FILE}" "${CA_FILE}"
echo "Exported the production FreeIPA public CA certificate to .runtime/freeipa-production/ca.crt."
