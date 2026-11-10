#!/usr/bin/env bash
set -euo pipefail

readonly conf=/opt/starrocks/be/conf/be.conf
if [[ ! -w "$conf" ]]; then
  echo "Disposable StarRocks BE startup blocked: BE configuration is not writable." >&2
  exit 2
fi

tmp_conf="$(mktemp "${conf}.XXXXXX")"
trap 'rm -f "$tmp_conf"' EXIT
awk '
  BEGIN { configured["priority_networks"] = "172.29.252.0/24" }
  /^[[:space:]]*priority_networks[[:space:]]*=/ {
    if (!seen++) print "priority_networks = " configured["priority_networks"]
    next
  }
  { print }
  END { if (!seen) print "priority_networks = " configured["priority_networks"] }
' "$conf" > "$tmp_conf"
chmod --reference="$conf" "$tmp_conf"
cat "$tmp_conf" > "$conf"
rm -f "$tmp_conf"
trap - EXIT

export STARROCKS_CONF_DIR=/opt/starrocks/be/conf
exec /opt/starrocks/be/bin/start_be.sh
