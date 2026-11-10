#!/usr/bin/env bash
set -euo pipefail
umask 077

readonly admin_password_file=/run/secrets/ranger-ipa-admin-password
readonly bind_password_file=/run/secrets/ranger-usersync-bind-password
readonly test_user_password_file=/run/secrets/ranger-test-user-password
readonly normalized_bind_password=/run/ranger-test-usersync-bind-password
readonly normalized_test_user_password=/run/ranger-test-user-password

cleanup() {
  rm -f "$normalized_bind_password" "$normalized_test_user_password"
}
trap cleanup EXIT

if [[ ! -s "$admin_password_file" ]]; then
  echo "Isolated FreeIPA bootstrap blocked: test admin credential is missing." >&2
  exit 2
fi
if [[ ! -s "$bind_password_file" ]] || ! grep -Eq '^R[a-f0-9]{64}a9$' "$bind_password_file"; then
  echo "Isolated FreeIPA bootstrap blocked: generated UserSync bind credential is missing or invalid." >&2
  exit 2
fi
if [[ ! -s "$test_user_password_file" ]] || ! grep -Eq '^R[a-f0-9]{64}a9$' "$test_user_password_file"; then
  echo "Isolated FreeIPA bootstrap blocked: synthetic test user credential is missing or invalid." >&2
  exit 2
fi

readonly ccache="FILE:/run/ranger-test-ipa-bootstrap.ccache"
readonly krb5_config=/run/ranger-test-ipa-bootstrap-krb5.conf
cleanup() {
  KRB5CCNAME="$ccache" kdestroy >/dev/null 2>&1 || true
  rm -f /run/ranger-test-ipa-bootstrap.ccache
  rm -f "$krb5_config"
}
trap cleanup EXIT
cat > "$krb5_config" <<'KRB5_EOF'
[libdefaults]
 default_realm = LAKEHOUSE.TEST
 dns_lookup_kdc = false
 rdns = false
 forwardable = true

[realms]
 LAKEHOUSE.TEST = {
  kdc = 127.0.0.1:88
  admin_server = 127.0.0.1:749
 }
KRB5_EOF
chmod 0600 "$krb5_config"
export KRB5_CONFIG="$krb5_config"
export KRB5CCNAME="$ccache"
if ! cat "$admin_password_file" | kinit admin@LAKEHOUSE.TEST; then
  echo "Isolated FreeIPA bootstrap could not authenticate as its test administrator." >&2
  exit 1
fi

ensure_group() {
  local group="$1"
  if ! ipa group-show "$group" >/dev/null 2>&1; then
    ipa group-add "$group" --desc="Isolated Ranger authorization test role" >/dev/null
  fi
}

ensure_user() {
  local username="$1"
  if ! ipa user-show "$username" >/dev/null 2>&1; then
    ipa user-add "$username" --first="Ranger" --last="Test" --random >/dev/null
  fi
}

ensure_group lakehouse-developers
ensure_group lakehouse-analysts
ensure_group lakehouse-writers
ensure_user developer-user
ensure_user analyst-user
ensure_user write-service-account
ensure_user ranger-usersync-bind

ensure_group_member() {
  local group="$1" username="$2" state
  state="$(ipa group-show "$group" --all --raw 2>/dev/null)" || {
    echo "Isolated FreeIPA could not inspect a test role group." >&2
    exit 1
  }
  if grep -Fq "uid=${username}," <<<"$state"; then
    return 0
  fi
  ipa group-add-member "$group" "--users=${username}" >/dev/null 2>&1 || {
    echo "Isolated FreeIPA could not attach a synthetic user to its test role group." >&2
    exit 1
  }
}
ensure_group_member lakehouse-developers developer-user
ensure_group_member lakehouse-analysts analyst-user
ensure_group_member lakehouse-writers write-service-account

# Secret files are newline-terminated for safe text-file storage. Normalize
# them before `ldappasswd -T`; otherwise LDAP clients that trim the newline
# authenticate with a different byte sequence than the one stored in IPA.
tr -d '\r\n' <"$bind_password_file" >"$normalized_bind_password"
tr -d '\r\n' <"$test_user_password_file" >"$normalized_test_user_password"
chmod 0600 "$normalized_bind_password" "$normalized_test_user_password"

readonly bind_dn='uid=ranger-usersync-bind,cn=users,cn=accounts,dc=lakehouse,dc=test'
for target_dn in "$bind_dn" "uid=developer-user,cn=users,cn=accounts,dc=lakehouse,dc=test" \
  "uid=analyst-user,cn=users,cn=accounts,dc=lakehouse,dc=test" \
  "uid=write-service-account,cn=users,cn=accounts,dc=lakehouse,dc=test"; do
  password_file="$normalized_test_user_password"
  [[ "$target_dn" != "$bind_dn" ]] || password_file="$normalized_bind_password"
  if ! ldappasswd -Y GSSAPI -H ldaps://ipa.ranger-test.lakehouse.test:636 \
    -T "$password_file" "$target_dn" >/dev/null 2>&1; then
    echo "Isolated FreeIPA could not set a synthetic account password." >&2
    exit 1
  fi
done
  if ! ldapwhoami -x -H ldaps://ipa.ranger-test.lakehouse.test:636 \
  -D "$bind_dn" \
  -y "$bind_password_file" >/dev/null 2>&1; then
  echo "Isolated UserSync LDAP bind check failed; no identities were synchronized." >&2
  exit 1
fi
echo "Isolated synthetic FreeIPA users/groups are present and the UserSync bind can authenticate."
