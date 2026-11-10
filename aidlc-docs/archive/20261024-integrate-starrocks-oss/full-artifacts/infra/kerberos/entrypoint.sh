#!/bin/bash
set -euo pipefail

REALM="${KERBEROS_REALM:-LAKEHOUSE.LOCAL}"
MASTER_PASSWORD_FILE="${KDC_MASTER_PASSWORD_FILE:-/run/secrets/kdc-master-password}"
SERVICE_KEYTAB="${HIVE_SERVICE_KEYTAB_FILE:-/keytabs/hive-metastore.keytab}"
SERVICE_PRINCIPAL="hive/hive-metastore@${REALM}"
BOOTSTRAP_PRINCIPAL="kadmin/provisioner@${REALM}"
ADMIN_PRINCIPAL="admin@${REALM}"
BOOTSTRAP_KEYTAB="/keytabs/kadmin-provisioner.keytab"
KDC_DATABASE="/var/lib/krb5kdc/principal"

if [[ ! -r "${MASTER_PASSWORD_FILE}" ]]; then
  echo "ERROR: KDC master password file is missing or unreadable." >&2
  exit 1
fi
if [[ ! -d "$(dirname "${SERVICE_KEYTAB}")" ]]; then
  echo "ERROR: Runtime credential directory is not mounted for Hive keytab output." >&2
  exit 1
fi

if [[ ! -e "${KDC_DATABASE}" ]]; then
  if [[ -s "${SERVICE_KEYTAB}" || -s "${BOOTSTRAP_KEYTAB}" ]]; then
    echo "ERROR: KDC database is absent but a provisioned keytab exists. Use the explicit reset procedure to reconcile state." >&2
    exit 1
  fi
  MASTER_PASSWORD="$(cat "${MASTER_PASSWORD_FILE}")"
  if [[ -z "${MASTER_PASSWORD}" ]]; then
    echo "ERROR: KDC master password file is empty." >&2
    exit 1
  fi
  kdb5_util create -r "${REALM}" -s -P "${MASTER_PASSWORD}" >/dev/null
  unset MASTER_PASSWORD
fi

if [[ ! -s "${BOOTSTRAP_KEYTAB}" ]]; then
  BOOTSTRAP_INFO="$(kadmin.local -r "${REALM}" -q "getprinc ${BOOTSTRAP_PRINCIPAL}" 2>&1 || true)"
  if [[ "${BOOTSTRAP_INFO}" == *"Principal does not exist"* ]]; then
    kadmin.local -r "${REALM}" -q "addprinc -randkey ${BOOTSTRAP_PRINCIPAL}" >/dev/null
  elif [[ "${BOOTSTRAP_INFO}" != *"Principal: ${BOOTSTRAP_PRINCIPAL}"* ]]; then
    echo "ERROR: Unable to inspect the Kerberos provisioning principal." >&2
    exit 1
  fi
  kadmin.local -r "${REALM}" -q "ktadd -norandkey -k ${BOOTSTRAP_KEYTAB} ${BOOTSTRAP_PRINCIPAL}" >/dev/null
  chmod 600 "${BOOTSTRAP_KEYTAB}"
fi

PRINCIPAL_INFO="$(kadmin.local -r "${REALM}" -q "getprinc ${SERVICE_PRINCIPAL}" 2>&1 || true)"
if [[ "${PRINCIPAL_INFO}" == *"Principal does not exist"* ]]; then
  kadmin.local -r "${REALM}" -q "addprinc -randkey ${SERVICE_PRINCIPAL}" >/dev/null
elif [[ "${PRINCIPAL_INFO}" != *"Principal: ${SERVICE_PRINCIPAL}"* ]]; then
  echo "ERROR: Unable to inspect the Hive Metastore service principal in the KDC database." >&2
  exit 1
fi

if [[ ! -s "${SERVICE_KEYTAB}" ]]; then
  kadmin.local -r "${REALM}" -q "ktadd -k ${SERVICE_KEYTAB} ${SERVICE_PRINCIPAL}" >/dev/null
  chmod 644 "${SERVICE_KEYTAB}"
fi

# MIT Kerberos' wildcard permission does not include key extraction. Grant
# the provisioner only add/inquire/extract access to the workload principals
# for which it issues keytabs. Its general account-management permissions and
# the platform administrator's permissions remain non-extracting.
{
  printf '%s aie %s\n' "${BOOTSTRAP_PRINCIPAL}" "admin@${REALM}"
  printf '%s aie %s\n' "${BOOTSTRAP_PRINCIPAL}" "write-service-account@${REALM}"
  printf '%s aie %s\n' "${BOOTSTRAP_PRINCIPAL}" "user_a@${REALM}"
  printf '%s aie %s\n' "${BOOTSTRAP_PRINCIPAL}" "user_b@${REALM}"
  printf '%s aie %s\n' "${BOOTSTRAP_PRINCIPAL}" "starrocks@${REALM}"
  printf '%s *\n%s *\n' "${BOOTSTRAP_PRINCIPAL}" "${ADMIN_PRINCIPAL}"
} > /etc/krb5kdc/kadm5.acl
chmod 600 /etc/krb5kdc/kadm5.acl

krb5kdc -n -r "${REALM}" &
KDC_PID=$!
kadmind -nofork -r "${REALM}" &
ADMIN_PID=$!

shutdown() {
  kill "${KDC_PID}" "${ADMIN_PID}" 2>/dev/null || true
  wait "${KDC_PID}" "${ADMIN_PID}" 2>/dev/null || true
}
trap shutdown TERM INT

set +e
wait -n "${KDC_PID}" "${ADMIN_PID}"
STATUS=$?
set -e
shutdown
exit "${STATUS}"
