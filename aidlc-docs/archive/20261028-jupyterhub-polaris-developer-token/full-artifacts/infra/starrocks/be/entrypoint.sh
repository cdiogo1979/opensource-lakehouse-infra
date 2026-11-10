#!/usr/bin/env bash
set -euo pipefail

readonly keytab=/run/credentials/starrocks.keytab
readonly krb5_config=/etc/krb5.conf
readonly rustfs_secret=/run/secrets/rustfs-starrocks-secret-key
readonly conf=/opt/starrocks/be/conf/be.conf
readonly krb5_option='-Djava.security.krb5.conf=/etc/krb5.conf'

for required_file in "$keytab" "$krb5_config" "$rustfs_secret"; do
  if [[ ! -r "$required_file" || ! -s "$required_file" ]]; then
    echo "StarRocks BE startup blocked: required credential/config file is unavailable." >&2
    exit 1
  fi
done

if [[ -z "${STARROCKS_PRINCIPAL:-}" || ! -w "$conf" || -z "${STARROCKS_FE_HOST:-}" ]]; then
  echo "StarRocks BE startup blocked: principal, FE host, or BE configuration is unavailable." >&2
  exit 1
fi

mkdir -p /run/krb5
chmod 0700 /run/krb5
export STARROCKS_CONF_DIR=/opt/starrocks/be/conf
. /usr/local/bin/starrocks-render-hadoop-config
export KRB5_CONFIG="$krb5_config"
export KRB5CCNAME=FILE:/run/krb5/ccache

if ! kinit -kt "$keytab" "$STARROCKS_PRINCIPAL" >/dev/null 2>&1; then
  echo "StarRocks BE startup blocked: initial Kerberos ticket acquisition failed." >&2
  exit 1
fi

if ! grep -Fq -- "$krb5_option" "$conf"; then
  tmp_conf="$(mktemp "${conf}.XXXXXX")"
  awk -v option="$krb5_option" '
    /^[[:space:]]*JAVA_OPTS[[:space:]]*=/ && !updated {
      line = $0
      if (line ~ /"[[:space:]]*$/) {
        sub(/"[[:space:]]*$/, " " option "\"", line)
      } else {
        line = line " " option
      }
      updated = 1
    }
    { print (line != "" ? line : $0); line = "" }
    END {
      if (!updated) print "JAVA_OPTS=\"" option "\""
    }
  ' "$conf" > "$tmp_conf"
  cat "$tmp_conf" > "$conf"
  rm -f "$tmp_conf"
fi

cron

exec /opt/starrocks/be/bin/start_be.sh
