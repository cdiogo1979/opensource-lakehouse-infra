#!/usr/bin/env bash
set -euo pipefail
umask 077
mkdir -p /var/lib/ranger-test-state
chmod 0700 /var/lib/ranger-test-state

readonly secret_dir=/run/secrets
readonly install_template=/home/ranger/scripts/ranger-admin-install.properties
readonly install_file=/opt/ranger/admin/install.properties

read_secret() {
  local path="$1"
  local kind="$2"
  if [[ ! -s "$path" || ! -r "$path" ]]; then
    echo "Ranger test Admin startup blocked: required secret file is missing." >&2
    exit 2
  fi
  local value
  value="$(<"$path")"
  if [[ "$kind" == account ]]; then
    if [[ ! "$value" =~ ^R[a-f0-9]{64}a9$ ]]; then
      echo "Ranger test Admin startup blocked: a generated account secret has an invalid format." >&2
      return 2
    fi
  elif [[ ! "$value" =~ ^[a-f0-9]{64}$ ]]; then
    echo "Ranger test Admin startup blocked: a generated secret has an invalid format." >&2
    return 2
  fi
  printf '%s' "$value"
}

if [[ ! -e /var/lib/ranger-test-state/.setupDone ]]; then
  cp "$install_template" "$install_file"
  chmod 0600 "$install_file"
  sed -i '/^db_host=/d; /^policymgr_external_url=/d; /^audit_store=/d' "$install_file"
  db_root_password="$(read_secret "$secret_dir/ranger-db-root-password" database)" || exit 2
  db_service_password="$(read_secret "$secret_dir/ranger-db-service-password" database)" || exit 2
  admin_password="$(read_secret "$secret_dir/ranger-admin-password" account)" || exit 2
  tagsync_password="$(read_secret "$secret_dir/ranger-tagsync-password" account)" || exit 2
  usersync_password="$(read_secret "$secret_dir/ranger-usersync-password" account)" || exit 2
  keyadmin_password="$(read_secret "$secret_dir/ranger-keyadmin-password" account)" || exit 2
  {
    printf 'db_host=ranger-test-db\n'
    printf 'db_root_password=%s\n' "$db_root_password"
    printf 'db_user=rangeradmin\n'
    printf 'db_password=%s\n' "$db_service_password"
    printf 'rangerAdmin_password=%s\n' "$admin_password"
    printf 'rangerTagsync_password=%s\n' "$tagsync_password"
    printf 'rangerUsersync_password=%s\n' "$usersync_password"
    printf 'keyadmin_password=%s\n' "$keyadmin_password"
    printf 'policymgr_external_url=http://ranger-test-admin:6080\n'
    printf 'audit_store=\n'
  } >> "$install_file"

  cd /opt/ranger/admin
  if ! ./set_globals.sh >/dev/null; then
    rm -f "$install_file"
    echo "Ranger test Admin global setup failed; inspect sanitized service logs." >&2
    exit 1
  fi
  if ! ./setup.sh >/dev/null; then
    rm -f "$install_file"
    echo "Ranger test Admin setup failed; inspect sanitized service logs." >&2
    exit 1
  fi
  rm -f "$install_file"
  if [[ ! -L /opt/ranger/admin/conf || ! -L /opt/ranger/admin/ews/webapp/WEB-INF/classes/conf \
      || ! -x /usr/bin/ranger-admin || ! -f /opt/ranger/admin/ews/webapp/WEB-INF/classes/conf/ranger-admin-site.xml ]]; then
    echo "Ranger test Admin setup incomplete; required configuration links were not installed." >&2
    exit 1
  fi
  touch /var/lib/ranger-test-state/.setupDone
fi

cd /opt/ranger/admin
./ews/ranger-admin-services.sh start >/dev/null
exec tail -F /opt/ranger/admin/ews/logs/catalina.out
