#!/bin/bash
set -euo pipefail
umask 077

REALM="${KERBEROS_REALM:-LAKEHOUSE.LOCAL}"
BOOTSTRAP_PRINCIPAL="kadmin/provisioner@${REALM}"
BOOTSTRAP_KEYTAB="/run/credentials/kadmin-provisioner.keytab"
KEYTAB_DIR="/run/credentials/keytabs"
PROVISIONER_MODE="${IDENTITY_PROVISIONER_MODE:-orchestrator}"

run_kerberos_provisioning() {
  if [[ ! -r "${BOOTSTRAP_KEYTAB}" ]]; then
    echo "Kerberos bootstrap credential unavailable." >&2
    return 1
  fi
  mkdir -p "${KEYTAB_DIR}"
  chmod 700 "${KEYTAB_DIR}"

  export KRB5CCNAME="FILE:/tmp/krb5cc-provisioner"
  trap 'kdestroy >/dev/null 2>&1 || true; rm -f /tmp/krb5cc-provisioner' EXIT
  kinit -kt "${BOOTSTRAP_KEYTAB}" "${BOOTSTRAP_PRINCIPAL}"

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
    elif [[ "${principal_info}" != *"Principal: ${principal}"* ]]; then
      echo "Unable to inspect Kerberos principal ${name}." >&2
      return 1
    fi

    if [[ -e "${keytab}" && ! -f "${keytab}" ]]; then
      echo "Kerberos keytab path for ${name} exists but is not a regular file." >&2
      return 1
    fi
    if [[ ! -s "${keytab}" ]]; then
      kadmin -p "${BOOTSTRAP_PRINCIPAL}" -k -t "${BOOTSTRAP_KEYTAB}" \
        -q "ktadd -norandkey -k ${keytab} ${principal}" >/dev/null
    fi
    if [[ "${name}" == "admin" || "${name}" == "user_a" || "${name}" == "user_b" ]]; then
      # Preserve the existing group-readable notebook identity contract.
      chmod 640 "${keytab}"
    else
      chmod 600 "${keytab}"
    fi

    kdestroy >/dev/null 2>&1 || true
    kinit -kt "${keytab}" "${principal}"
    kdestroy >/dev/null 2>&1 || true
  }

  for identity in admin write-service-account user_a user_b starrocks; do
    ensure_principal "${identity}"
  done
}

if [[ "${PROVISIONER_MODE}" == "kerberos" ]]; then
  run_kerberos_provisioning
  exit $?
fi

if [[ "${PROVISIONER_MODE}" != "orchestrator" ]]; then
  echo "Unsupported identity provisioner mode." >&2
  exit 2
fi

kerberos_status=0
rustfs_status=0
if IDENTITY_PROVISIONER_MODE=kerberos "${BASH_SOURCE[0]}" >/dev/null 2>&1; then
  echo "Kerberos provider: ready"
else
  kerberos_status=$?
  echo "Kerberos provider: failed (provisioning-error, exit ${kerberos_status}); inspect KDC and credential configuration, then reconcile before rerunning." >&2
fi

if provision-rustfs-identities; then
  echo "RustFS provider: ready"
else
  rustfs_status=$?
  echo "RustFS provider: failed; inspect the redacted provider category above and reconcile configuration or policy drift before rerunning." >&2
fi

if (( kerberos_status != 0 || rustfs_status != 0 )); then
  echo "Identity provider aggregate: failed (Kerberos=${kerberos_status}, RustFS=${rustfs_status})." >&2
  exit 1
fi

if ! provision-postgres-roles; then
  echo "PostgreSQL identity setup failed; inspect the safe PostgreSQL diagnostic and reconcile before rerunning." >&2
  exit 1
fi

touch /run/identity-status/rustfs-ready
echo "Identity provisioning completed. Run scripts/provision-identities.sh on the host to apply the Hive service credential and restart Hive."
