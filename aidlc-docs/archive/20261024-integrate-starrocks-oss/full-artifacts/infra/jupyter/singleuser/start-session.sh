#!/usr/bin/env bash
set -euo pipefail
set +x

KEYTAB_FILE="/run/credentials/identity.keytab"
ACCESS_KEY_FILE="/run/credentials/rustfs-access-key"
SECRET_KEY_FILE="/run/credentials/rustfs-secret-key"
TICKET_CACHE="${KRB5CCNAME:-FILE:/run/krb5/ccache}"
PRINCIPAL="${KERBEROS_PRINCIPAL:?KERBEROS_PRINCIPAL is required}"

for path in "${KEYTAB_FILE}" "${ACCESS_KEY_FILE}" "${SECRET_KEY_FILE}"; do
  if [[ ! -s "${path}" || ! -r "${path}" ]]; then
    echo "ERROR: A required identity file is missing or unreadable: $(basename "${path}")." >&2
    exit 1
  fi
done

if [[ ! -d /run/krb5 || ! -w /run/krb5 ]]; then
  echo "ERROR: The private Kerberos cache directory is unavailable." >&2
  exit 1
fi

export AWS_ACCESS_KEY_ID
AWS_ACCESS_KEY_ID="$(tr -d '\r\n' < "${ACCESS_KEY_FILE}")"
export AWS_SECRET_ACCESS_KEY
AWS_SECRET_ACCESS_KEY="$(tr -d '\r\n' < "${SECRET_KEY_FILE}")"
export AWS_EC2_METADATA_DISABLED=true
export SPARK_SUBMIT_OPTS="${SPARK_SUBMIT_OPTS:+${SPARK_SUBMIT_OPTS} }-Djava.security.krb5.conf=/etc/krb5.conf"

if [[ -z "${AWS_ACCESS_KEY_ID}" || -z "${AWS_SECRET_ACCESS_KEY}" ]]; then
  echo "ERROR: The mounted RustFS identity is empty." >&2
  exit 1
fi

kinit -c "${TICKET_CACHE}" -kt "${KEYTAB_FILE}" "${PRINCIPAL}"
if ! klist -s -c "${TICKET_CACHE}"; then
  echo "ERROR: Kerberos did not establish the requested session identity." >&2
  exit 1
fi
export KRB5CCNAME="${TICKET_CACHE}"

cleanup_session() {
  kdestroy -c "${TICKET_CACHE}" >/dev/null 2>&1 || true
  rm -f /run/krb5/ccache
}
forward_signal() {
  local signal="$1"
  if [[ -n "${child_pid:-}" ]]; then
    kill -s "${signal}" "${child_pid}" 2>/dev/null || true
  fi
}
trap cleanup_session EXIT
trap 'forward_signal TERM' TERM
trap 'forward_signal INT' INT

"$@" &
child_pid=$!
set +e
wait "${child_pid}"
status=$?
set -e
exit "${status}"
