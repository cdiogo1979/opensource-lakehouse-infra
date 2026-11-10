#!/usr/bin/env bash
set -euo pipefail
umask 077

readonly install_file=/opt/ranger/install.properties
readonly bind_password_file=/run/secrets/ranger-usersync-bind-password
readonly ca_file=/run/freeipa-ca/ca.crt

for required in /run/secrets/ranger-usersync-password "$bind_password_file" "$ca_file"; do
  if [[ ! -s "$required" ]]; then
    echo "Ranger UserSync startup blocked: a required protected credential or CA file is missing." >&2
    exit 2
  fi
done

if ! grep -Eq '^R[a-f0-9]{64}a9$' /run/secrets/ranger-usersync-password; then
  echo "Ranger UserSync startup blocked: the generated service credential has an invalid format." >&2
  exit 2
fi

readonly bind_password="$(cat "$bind_password_file")"
if [[ ! "$bind_password" =~ ^R[a-f0-9]{64}a9$ ]]; then
  echo "Ranger UserSync startup blocked: the isolated LDAP bind credential has an invalid format." >&2
  exit 2
fi

truststore="$JAVA_HOME/lib/security/cacerts"
if [[ ! -f "$truststore" ]]; then
  truststore="$JAVA_HOME/jre/lib/security/cacerts"
fi
if [[ ! -f "$truststore" ]]; then
  echo "Ranger UserSync startup blocked: the Java truststore was not found." >&2
  exit 2
fi
keytool -importcert -noprompt -alias ranger-test-freeipa-ca -file "$ca_file" \
  -keystore "$truststore" -storepass changeit >/dev/null 2>&1 \
  || keytool -list -keystore "$truststore" -storepass changeit \
       -alias ranger-test-freeipa-ca >/dev/null 2>&1

chmod 0600 "$install_file"
python3 - "$install_file" <<'PY'
from pathlib import Path
import sys

target_keys = {
    "policy_mgr_url",
    "sync_source",
    "sync_interval",
    "rangerusersync_password",
    "sync_ldap_url",
    "sync_ldap_bind_dn",
    "sync_ldap_bind_password",
    "sync_ldap_search_base",
    "sync_ldap_user_search_base",
    "sync_ldap_user_name_attribute",
    "sync_ldap_user_search_filter",
    "sync_ldap_user_group_name_attribute",
    "sync_group_search_enabled",
    "sync_group_user_map_sync_enabled",
    "sync_group_search_base",
    "sync_group_object_class",
    "sync_group_name_attribute",
    "sync_group_member_attribute_name",
    "sync_ldap_group_search_filter",
}
path = Path(sys.argv[1])
lines = path.read_text().splitlines()
remaining = []
for line in lines:
    stripped = line.strip()
    key = stripped.split("=", 1)[0].strip().casefold() if "=" in stripped and not stripped.startswith("#") else ""
    if key not in target_keys:
        remaining.append(line)
path.write_text("\n".join(remaining) + "\n")
PY
{
  printf 'POLICY_MGR_URL = http://ranger-test-admin:6080\n'
  printf 'SYNC_SOURCE = ldap\n'
  printf 'SYNC_INTERVAL = 1\n'
  printf 'rangerUsersync_password = %s\n' "$(cat /run/secrets/ranger-usersync-password)"
  printf 'SYNC_LDAP_URL = ldaps://ipa.ranger-test.lakehouse.test:636\n'
  printf 'SYNC_LDAP_BIND_DN = uid=ranger-usersync-bind,cn=users,cn=accounts,dc=lakehouse,dc=test\n'
  printf 'SYNC_LDAP_BIND_PASSWORD = %s\n' "$bind_password"
  printf 'SYNC_LDAP_SEARCH_BASE = cn=accounts,dc=lakehouse,dc=test\n'
  printf 'SYNC_LDAP_USER_SEARCH_BASE = cn=users,cn=accounts,dc=lakehouse,dc=test\n'
  printf 'SYNC_LDAP_USER_NAME_ATTRIBUTE = uid\n'
  printf 'SYNC_LDAP_USER_SEARCH_FILTER = (|(uid=developer-user)(uid=analyst-user)(uid=write-service-account))\n'
  printf 'SYNC_LDAP_USER_GROUP_NAME_ATTRIBUTE = memberof\n'
  printf 'SYNC_GROUP_SEARCH_ENABLED = true\n'
  printf 'SYNC_GROUP_USER_MAP_SYNC_ENABLED = true\n'
  printf 'SYNC_GROUP_SEARCH_BASE = cn=groups,cn=accounts,dc=lakehouse,dc=test\n'
  printf 'SYNC_GROUP_OBJECT_CLASS = groupOfNames\n'
  printf 'SYNC_GROUP_NAME_ATTRIBUTE = cn\n'
  printf 'SYNC_GROUP_MEMBER_ATTRIBUTE_NAME = member\n'
  printf 'SYNC_LDAP_GROUP_SEARCH_FILTER = (cn=lakehouse-*)\n'
} >> "$install_file"

cd /opt/ranger
run_sanitized_setup() {
  "$@" 2>&1 | python3 -c '
import re
import sys

sensitive = re.compile(r"(?i)(password|passwd|secret|token|credential|bind[_ -]?dn|keytab)")
diagnostic = re.compile(r"(?i)(error|exception|failed|failure|caused by|fatal|denied|unable|not found)")
for raw in sys.stdin:
    line = raw.rstrip("\n")
    if not diagnostic.search(line):
        continue
    if sensitive.search(line):
        print("[setup diagnostic omitted because it references credential material]")
        continue
    line = re.sub(r"R[a-f0-9]{64}a9", "[REDACTED-CREDENTIAL]", line)
    line = re.sub(r"(?i)(https?://)[^/@\\s:]+:[^/@\\s]+@", r"\\1[REDACTED]@", line)
    print(line[:1000])
'
}

if ! run_sanitized_setup ./set_globals.sh || ! run_sanitized_setup python3 ./setup.py; then
  rm -f "$install_file"
  echo "Ranger UserSync installation failed; inspect sanitized service logs." >&2
  exit 1
fi
rm -f "$install_file"
if [[ ! -s /etc/ranger/usersync/conf/ranger-ugsync-site.xml ]]; then
  echo "Ranger UserSync setup completed without generating its required LDAP configuration." >&2
  exit 1
fi

# Ranger's setup script creates these parent directories with restrictive
# defaults. The ranger service account needs traversal; configuration files
# beneath the usersync directory stay owner-restricted.
chmod 0755 /etc/ranger /etc/ranger/usersync

# The pinned Ranger base image's Logback parser treats the UserSync rolling
# date pattern as a timezone and aborts the JVM. Use a plain file appender in
# this disposable test service; the test container itself keeps the log.
sed -i \
  's#ch.qos.logback.core.rolling.RollingFileAppender#ch.qos.logback.core.FileAppender#; /<rollingPolicy/,/<\/rollingPolicy>/d' \
  /etc/ranger/usersync/conf/logback.xml
chown ranger:ranger /etc/ranger/usersync/conf/logback.xml
chmod 0600 /etc/ranger/usersync/conf/logback.xml

cd /opt/ranger
rm -f /var/run/ranger/usersync.pid
if ! run_sanitized_setup su -s /bin/bash ranger -c 'cd /opt/ranger && ./ranger-usersync-services.sh start'; then
  echo "Ranger UserSync service startup failed; inspect sanitized service diagnostics." >&2
  exit 1
fi
exec tail -F /var/log/ranger/usersync/auth.log
