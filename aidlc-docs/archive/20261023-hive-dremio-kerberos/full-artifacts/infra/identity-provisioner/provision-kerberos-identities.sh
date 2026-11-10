#!/bin/bash
set -euo pipefail
umask 077

REALM="${KERBEROS_REALM:-LAKEHOUSE.LOCAL}"
BOOTSTRAP_PRINCIPAL="kadmin/provisioner@${REALM}"
BOOTSTRAP_KEYTAB="/run/credentials/kadmin-provisioner.keytab"
KEYTAB_DIR="/run/credentials/keytabs"

if [[ ! -r "${BOOTSTRAP_KEYTAB}" ]]; then
  echo "ERROR: Kerberos provisioning keytab is missing or unreadable."
  exit 1
fi
mkdir -p "${KEYTAB_DIR}"

export KRB5CCNAME="FILE:/tmp/krb5cc-provisioner"
kinit -kt "${BOOTSTRAP_KEYTAB}" "${BOOTSTRAP_PRINCIPAL}"
trap 'kdestroy >/dev/null 2>&1 || true; rm -f /tmp/krb5cc-provisioner' EXIT

ensure_principal() {
  local name="$1"
  local principal="${name}@${REALM}"
  local keytab="${KEYTAB_DIR}/${name}.keytab"

  local principal_info
  principal_info="$(kadmin -p "${BOOTSTRAP_PRINCIPAL}" -k -t "${BOOTSTRAP_KEYTAB}" \
      -q "getprinc ${principal}" 2>&1 || true)"
  if [[ "${principal_info}" == *"Principal does not exist"* ]]; then
    kadmin -p "${BOOTSTRAP_PRINCIPAL}" -k -t "${BOOTSTRAP_KEYTAB}" \
      -q "addprinc -randkey ${principal}" >/dev/null
    echo "Kerberos ${name}: created"
  elif [[ "${principal_info}" == *"Principal: ${principal}"* ]]; then
    echo "Kerberos ${name}: already-present"
  else
    echo "ERROR: Unable to inspect Kerberos principal ${name}."
    exit 1
  fi

  if [[ ! -s "${keytab}" ]]; then
    kadmin -p "${BOOTSTRAP_PRINCIPAL}" -k -t "${BOOTSTRAP_KEYTAB}" \
      -q "ktadd -norandkey -k ${keytab} ${principal}" >/dev/null
  fi

  if [[ "${name}" == "dremio" || "${name}" == "admin" || "${name}" == "user_a" || "${name}" == "user_b" ]]; then
    # Host credential directories are owner-only. The matching Jupyter
    # container receives only its individual keytab and this supplementary GID.
    chmod 640 "${keytab}"
  else
    chmod 600 "${keytab}"
  fi

  kinit -kt "${keytab}" "${principal}"
  kdestroy >/dev/null 2>&1 || true
}

for identity in admin write-service-account user_a user_b dremio; do
  ensure_principal "${identity}"
done

echo "Kerberos identities: complete"
provision-rustfs-identities
provision-postgres-roles

touch /run/identity-status/rustfs-ready
echo "Identity provisioning completed. Run scripts/provision-identities.sh on the host to apply the Hive service credential and restart Hive."
