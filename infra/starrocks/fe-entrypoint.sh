#!/bin/bash
# StarRocks FE entrypoint: start from the tracked fe.conf and add the TLS keystore
# settings, whose password comes from a protected mounted file rather than the
# tracked config or the container environment.
set -euo pipefail

conf=/opt/starrocks/fe/conf/fe.conf
password="$(head -n 1 /run/secrets/starrocks_keystore_password)"
{
  cat /opt/lakehouse/fe.conf
  echo "ssl_keystore_location = /run/secrets/starrocks_fe_keystore.p12"
  echo "ssl_keystore_password = ${password}"
  echo "ssl_key_password = ${password}"
} > "$conf"
chmod 600 "$conf"
unset password
exec /opt/starrocks/fe/bin/start_fe.sh --host_type FQDN
