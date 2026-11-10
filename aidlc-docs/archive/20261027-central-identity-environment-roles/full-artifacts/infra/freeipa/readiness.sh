#!/usr/bin/env bash
set -euo pipefail
umask 077

readonly realm="${KERBEROS_REALM:-LAKEHOUSE.LOCAL}"
readonly hostname="${FREEIPA_HOSTNAME:-ipa.lakehouse.local}"
readonly principal="host/${hostname}@${realm}"
readonly cache="FILE:/run/freeipa-readiness.ccache"

if python3 /usr/local/sbin/patch-httpd-redirects.py; then
  systemctl reload httpd
else
  patch_status=$?
  if [[ "${patch_status}" -ne 1 ]]; then
    exit "${patch_status}"
  fi
fi

cleanup() {
  KRB5CCNAME="${cache}" kdestroy >/dev/null 2>&1 || true
  rm -f /run/freeipa-readiness.ccache
}
trap cleanup EXIT

command -v timeout >/dev/null 2>&1 || exit 1
command -v kinit >/dev/null 2>&1 || exit 1
command -v ldapsearch >/dev/null 2>&1 || exit 1
[[ -r /etc/krb5.keytab && -r /etc/ipa/ca.crt ]] || exit 1

export KRB5CCNAME="${cache}"
timeout 10s kinit -k -t /etc/krb5.keytab "${principal}" >/dev/null 2>&1
timeout 10s ldapsearch -LLL -Q -Y GSSAPI \
  -H "ldaps://${hostname}" \
  -o TLS_CACERT=/etc/ipa/ca.crt \
  -o TLS_REQCERT=demand \
  -b "" -s base namingContexts >/dev/null 2>&1
