#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

CA_DIR=".runtime/freeipa"
CA_FILE="${CA_DIR}/ca.crt"
TMP_FILE="${CA_FILE}.tmp"
mkdir -p "${CA_DIR}"
chmod 700 "${CA_DIR}"
rm -f "${TMP_FILE}"

if ! docker cp iceberg-poc-freeipa-validation:/etc/ipa/ca.crt "${TMP_FILE}" >/dev/null; then
  echo "Unable to export the FreeIPA public CA certificate; confirm the validation server is installed." >&2
  exit 1
fi
if ! openssl x509 -in "${TMP_FILE}" -noout >/dev/null 2>&1; then
  rm -f "${TMP_FILE}"
  echo "The FreeIPA CA export is not a valid X.509 certificate." >&2
  exit 1
fi
chmod 644 "${TMP_FILE}"

if [[ -e "${CA_FILE}" ]]; then
  if cmp -s "${CA_FILE}" "${TMP_FILE}"; then
    rm -f "${TMP_FILE}"
    echo "FreeIPA public CA certificate is already current."
    exit 0
  fi
  rm -f "${TMP_FILE}"
  echo "A different FreeIPA CA certificate is already present; review it before replacement." >&2
  exit 1
fi
mv "${TMP_FILE}" "${CA_FILE}"
echo "Exported the FreeIPA public CA certificate to ${CA_FILE}."
