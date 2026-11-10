#!/usr/bin/env bash
set -euo pipefail

readonly conf=/opt/starrocks/fe/conf/fe.conf
readonly keystore_password=/run/sql-tls/keystore-password
readonly ldap_ca=/run/ldap/freeipa-test-ca.crt

for required_file in "$keystore_password" "$ldap_ca" /run/sql-tls/starrocks-test.jks; do
  if [[ ! -r "$required_file" || ! -s "$required_file" ]]; then
    echo "Disposable StarRocks FE startup blocked: a test-only TLS file is unavailable." >&2
    exit 2
  fi
done

if [[ ! -w "$conf" ]]; then
  echo "Disposable StarRocks FE startup blocked: FE configuration is not writable." >&2
  exit 2
fi

tmp_conf="$(mktemp "${conf}.XXXXXX")"
trap 'rm -f "$tmp_conf"' EXIT
awk '
  BEGIN {
    if ((getline keystore_password < "/run/sql-tls/keystore-password") <= 0) exit 2
    close("/run/sql-tls/keystore-password")
    configured["priority_networks"] = "172.29.252.0/24"
    configured["authentication_ldap_simple_server_host"] = "ipa.ranger-test.lakehouse.test"
    configured["authentication_ldap_simple_server_port"] = "636"
    configured["authentication_ldap_simple_bind_dn_pattern"] = "uid=${USER},cn=users,cn=accounts,dc=lakehouse,dc=test"
    configured["authentication_ldap_simple_ssl_conn_allow_insecure"] = "false"
    configured["authentication_ldap_simple_ssl_conn_trust_store_path"] = "/run/ldap/freeipa-test-ca.crt"
    configured["group_provider"] = "lakehouse_freeipa_groups"
    configured["ssl_force_secure_transport"] = "true"
    configured["ssl_keystore_location"] = "/run/sql-tls/starrocks-test.jks"
    configured["ssl_keystore_password"] = keystore_password
    configured["ssl_key_password"] = keystore_password
    keys[1] = "priority_networks"
    keys[2] = "authentication_ldap_simple_server_host"
    keys[3] = "authentication_ldap_simple_server_port"
    keys[4] = "authentication_ldap_simple_bind_dn_pattern"
    keys[5] = "authentication_ldap_simple_ssl_conn_allow_insecure"
    keys[6] = "authentication_ldap_simple_ssl_conn_trust_store_path"
    keys[7] = "ssl_force_secure_transport"
    keys[8] = "ssl_keystore_location"
    keys[9] = "ssl_keystore_password"
    keys[10] = "ssl_key_password"
    keys[11] = "group_provider"
  }
  /^[[:space:]]*JAVA_OPTS[[:space:]]*=/ {
    line = $0
    if (line ~ /-Xmx[^[:space:]]+/) sub(/-Xmx[^[:space:]]+/, "-Xmx2g", line)
    else line = line " -Xmx2g"
    if (line ~ /-Xms[^[:space:]]+/) sub(/-Xms[^[:space:]]+/, "-Xms1g", line)
    else line = line " -Xms1g"
    print line
    next
  }
  {
    for (i = 1; i <= 11; i++) {
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
    for (i = 1; i <= 11; i++) {
      key = keys[i]
      if (!seen[key]) print key " = " configured[key]
    }
  }
' "$conf" > "$tmp_conf"
chmod --reference="$conf" "$tmp_conf"
cat "$tmp_conf" > "$conf"
rm -f "$tmp_conf"
trap - EXIT

export STARROCKS_CONF_DIR=/opt/starrocks/fe/conf
exec /opt/starrocks/fe/bin/start_fe.sh --host_type FQDN
