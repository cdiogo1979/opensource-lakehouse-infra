#!/usr/bin/env bash
set -euo pipefail

readonly keytab=/run/credentials/starrocks.keytab
readonly krb5_config=/etc/krb5.conf
readonly rustfs_secret=/run/secrets/rustfs-starrocks-secret-key
readonly conf=/opt/starrocks/fe/conf/fe.conf
readonly krb5_option='-Djava.security.krb5.conf=/etc/krb5.conf'

for required_file in "$keytab" "$krb5_config" "$rustfs_secret"; do
  if [[ ! -r "$required_file" || ! -s "$required_file" ]]; then
    echo "StarRocks FE startup blocked: required credential/config file is unavailable." >&2
    exit 1
  fi
done

if [[ -z "${STARROCKS_PRINCIPAL:-}" || ! -w "$conf" ]]; then
  echo "StarRocks FE startup blocked: principal or FE configuration is unavailable." >&2
  exit 1
fi

mkdir -p /run/krb5
chmod 0700 /run/krb5
export STARROCKS_CONF_DIR=/opt/starrocks/fe/conf
. /usr/local/bin/starrocks-render-hadoop-config
export KRB5_CONFIG="$krb5_config"
export KRB5CCNAME=FILE:/run/krb5/ccache

if ! kinit -kt "$keytab" "$STARROCKS_PRINCIPAL" >/dev/null 2>&1; then
  echo "StarRocks FE startup blocked: initial Kerberos ticket acquisition failed." >&2
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

# The LDAP group provider is configured by the native role bootstrap. Keep
# its cluster-wide selection in fe.conf so native users continue resolving
# FreeIPA groups after an FE restart.
tmp_conf="$(mktemp "${conf}.XXXXXX")"
awk '
  /^[[:space:]]*group_provider[[:space:]]*=/ {
    if (!updated) print "group_provider = lakehouse_freeipa_groups"
    updated = 1
    next
  }
  { print }
  END {
    if (!updated) print "group_provider = lakehouse_freeipa_groups"
  }
' "$conf" > "$tmp_conf"
chmod --reference="$conf" "$tmp_conf"
cat "$tmp_conf" > "$conf"
rm -f "$tmp_conf"

# LDAP authentication is opt-in via the separate production Compose override.
# Keep the StarRocks SQL listener TLS-only whenever LDAP passwords can be used.
if [[ -n "${STARROCKS_LDAP_SERVER_HOST:-}" ]]; then
  readonly ldap_ca=/run/ldap/freeipa-production-ca.crt
  readonly sql_keystore=/run/sql-tls/starrocks-production.jks
  readonly sql_keystore_password=/run/sql-tls/keystore-password
  if [[ ! "${STARROCKS_LDAP_SERVER_HOST}" =~ ^[A-Za-z0-9.-]+$ \
      || "${STARROCKS_LDAP_SERVER_PORT:-}" != 636 \
      || "${STARROCKS_LDAP_BIND_DN_PATTERN:-}" != 'uid=${USER},cn=users,cn=accounts,dc=lakehouse,dc=local' ]]; then
    echo "StarRocks FE startup blocked: production LDAP settings are invalid." >&2
    exit 1
  fi
  for required_file in "$ldap_ca" "$sql_keystore" "$sql_keystore_password"; do
    if [[ -L "$required_file" || ! -r "$required_file" || ! -s "$required_file" ]]; then
      echo "StarRocks FE startup blocked: production LDAP/TLS trust material is unavailable." >&2
      exit 1
    fi
  done
  if [[ "$(stat -c '%a' "$sql_keystore_password")" != 400 && "$(stat -c '%a' "$sql_keystore_password")" != 600 ]]; then
    echo "StarRocks FE startup blocked: SQL keystore password file permissions are unsafe." >&2
    exit 1
  fi

  tmp_conf="$(mktemp "${conf}.XXXXXX")"
  awk '
    BEGIN {
      if ((getline password < "/run/sql-tls/keystore-password") <= 0) exit 2
      close("/run/sql-tls/keystore-password")
      configured["authentication_ldap_simple_server_host"] = ENVIRON["STARROCKS_LDAP_SERVER_HOST"]
      configured["authentication_ldap_simple_server_port"] = ENVIRON["STARROCKS_LDAP_SERVER_PORT"]
      configured["authentication_ldap_simple_bind_dn_pattern"] = ENVIRON["STARROCKS_LDAP_BIND_DN_PATTERN"]
      configured["authentication_ldap_simple_ssl_conn_allow_insecure"] = "false"
      configured["authentication_ldap_simple_ssl_conn_trust_store_path"] = "/run/ldap/freeipa-production-ca.crt"
      configured["group_provider"] = "lakehouse_freeipa_groups"
      configured["ssl_force_secure_transport"] = "true"
      configured["ssl_keystore_location"] = "/run/sql-tls/starrocks-production.jks"
      configured["ssl_keystore_password"] = password
      configured["ssl_key_password"] = password
      keys[1] = "authentication_ldap_simple_server_host"
      keys[2] = "authentication_ldap_simple_server_port"
      keys[3] = "authentication_ldap_simple_bind_dn_pattern"
      keys[4] = "authentication_ldap_simple_ssl_conn_allow_insecure"
      keys[5] = "authentication_ldap_simple_ssl_conn_trust_store_path"
      keys[6] = "group_provider"
      keys[7] = "ssl_force_secure_transport"
      keys[8] = "ssl_keystore_location"
      keys[9] = "ssl_keystore_password"
      keys[10] = "ssl_key_password"
    }
    {
      for (i = 1; i <= 10; i++) {
        key = keys[i]
        if ($0 ~ "^[[:space:]]*" key "[[:space:]]*=") {
          if (!seen[key]) print key " = " configured[key]
          seen[key] = 1
          next
        }
      }
      print
    }
    END {
      for (i = 1; i <= 10; i++) {
        key = keys[i]
        if (!seen[key]) print key " = " configured[key]
      }
    }
  ' "$conf" > "$tmp_conf"
  chmod --reference="$conf" "$tmp_conf"
  cat "$tmp_conf" > "$conf"
  rm -f "$tmp_conf"
fi

cron
exec /opt/starrocks/fe/bin/start_fe.sh --host_type FQDN
