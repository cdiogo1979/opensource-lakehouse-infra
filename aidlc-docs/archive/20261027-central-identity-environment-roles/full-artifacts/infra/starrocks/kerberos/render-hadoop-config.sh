#!/usr/bin/env bash
set -euo pipefail

readonly secret_file=/run/secrets/rustfs-starrocks-secret-key
readonly template=/etc/starrocks/core-site.xml.template
readonly runtime_conf=/run/krb5
readonly starrocks_conf="${STARROCKS_CONF_DIR:-}"

if [[ -z "$starrocks_conf" || ! -d "$starrocks_conf" || ! -w "$starrocks_conf" || ! -r "$secret_file" || ! -s "$secret_file" || ! -r "$template" ]]; then
  echo "StarRocks startup blocked: protected Hadoop S3 configuration input is unavailable." >&2
  return 1 2>/dev/null || exit 1
fi

local_secret="$(<"$secret_file")"
if [[ ! "$local_secret" =~ ^[[:xdigit:]]{80}$ ]]; then
  echo "StarRocks startup blocked: protected Hadoop S3 credential has an invalid format." >&2
  return 1 2>/dev/null || exit 1
fi

chmod 0700 "$runtime_conf"
if ! grep -Fq -- '__RUSTFS_SECRET_KEY__' "$template"; then
  echo "StarRocks startup blocked: Hadoop S3 configuration template is invalid." >&2
  return 1 2>/dev/null || exit 1
fi

umask 077
sed "s/__RUSTFS_SECRET_KEY__/${local_secret}/g" "$template" > "$runtime_conf/core-site.xml"
chmod 0600 "$runtime_conf/core-site.xml"
ln -sfn "$runtime_conf/core-site.xml" "$starrocks_conf/core-site.xml"
unset local_secret
export HADOOP_CONF_DIR="$starrocks_conf"
