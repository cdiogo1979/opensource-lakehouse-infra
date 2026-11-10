#!/bin/bash
set -euo pipefail

REALM="${KERBEROS_REALM:-LAKEHOUSE.LOCAL}"
PRINCIPAL="hive/hive-metastore@${REALM}"
KEYTAB="${HIVE_SERVICE_KEYTAB_FILE:-/keytabs/hive-metastore.keytab}"
CCACHE="FILE:/tmp/krb5cc-health"

KRB5CCNAME="${CCACHE}" kinit -kt "${KEYTAB}" "${PRINCIPAL}" >/dev/null 2>&1
KRB5CCNAME="${CCACHE}" kvno "${PRINCIPAL}" >/dev/null 2>&1
KRB5CCNAME="${CCACHE}" kdestroy >/dev/null 2>&1 || true

