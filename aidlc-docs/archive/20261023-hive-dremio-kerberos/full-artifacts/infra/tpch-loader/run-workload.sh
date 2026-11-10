#!/usr/bin/env bash
set -euo pipefail

INPUT_DIR="${TPCH_INPUT_DIR:-/opt/tpch/data}"
RESULTS_DIR="${TPCH_RESULTS_DIR:-/run/results}"
KEYTAB_FILE="/run/credentials/write-service-account.keytab"
TICKET_CACHE="FILE:/run/krb5/ccache"
PRINCIPAL="${WRITE_PRINCIPAL:?WRITE_PRINCIPAL is required}"

mkdir -p /run/krb5 "${RESULTS_DIR}"
chmod 700 /run/krb5

cleanup_ticket() {
  kdestroy -c "${TICKET_CACHE}" >/dev/null 2>&1 || true
  rm -f /run/krb5/ccache
}
trap cleanup_ticket EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

for name in customer lineitem nation orders part partsupp region supplier; do
  if [[ ! -s "${INPUT_DIR}/${name}.tbl" ]]; then
    echo "ERROR: Required TPCH input is missing: ${name}.tbl" >&2
    exit 1
  fi
done

for name in rustfs-writer-access-key rustfs-writer-secret-key; do
  if [[ ! -s "/run/secrets/${name}" ]]; then
    echo "ERROR: Required workload credential is unavailable: ${name}" >&2
    exit 1
  fi
done

if [[ ! -s "${KEYTAB_FILE}" ]]; then
  echo "ERROR: Writer keytab is unavailable." >&2
  exit 1
fi

kinit -c "${TICKET_CACHE}" -kt "${KEYTAB_FILE}" "${PRINCIPAL}"
klist -s -c "${TICKET_CACHE}"
export KRB5CCNAME="${TICKET_CACHE}"
/opt/spark/bin/spark-submit \
  --master 'local[2]' \
  --conf spark.driver.extraJavaOptions="${SPARK_SUBMIT_OPTS}" \
  /opt/tpch/load_tpch.py
