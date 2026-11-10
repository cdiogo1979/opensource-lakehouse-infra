#!/usr/bin/env bash
set -euo pipefail

readonly keytab=/run/credentials/starrocks.keytab
principal="${STARROCKS_PRINCIPAL:-}"
export KRB5_CONFIG=/etc/krb5.conf
export KRB5CCNAME=FILE:/run/krb5/ccache

if [[ -z "$principal" ]]; then
  realm="$(awk '$1 == "default_realm" { print $3; exit }' "$KRB5_CONFIG" 2>/dev/null || true)"
  if [[ -n "$realm" ]]; then
    principal="starrocks@${realm}"
  fi
fi

if [[ -z "$principal" || ! -r "$keytab" ]]; then
  printf '%s\n' 'StarRocks Kerberos ticket refresh failed: credential unavailable.' > /proc/1/fd/2
  exit 1
fi

if kinit -kt "$keytab" "$principal" >/dev/null 2>&1; then
  printf '%s\n' 'StarRocks Kerberos ticket refreshed.' > /proc/1/fd/1
else
  printf '%s\n' 'StarRocks Kerberos ticket refresh failed; current ticket may remain usable.' > /proc/1/fd/2
  exit 1
fi
