#!/usr/bin/env bash
set -euo pipefail
umask 077

readonly admin_password_file=/run/secrets/freeipa-admin-password
readonly reader_password_file=/run/secrets/freeipa-starrocks-reader-password
readonly writer_password_file=/run/secrets/freeipa-writer-password
readonly temp_reader_password=/run/starrocks-reader-password
readonly temp_writer_password=/run/starrocks-writer-password
readonly realm="${KERBEROS_REALM:-LAKEHOUSE.LOCAL}"
readonly reader_dn="uid=starrocks-ldap-reader,cn=users,cn=accounts,dc=lakehouse,dc=local"
readonly writer_dn="uid=write-service-account,cn=users,cn=accounts,dc=lakehouse,dc=local"
readonly cache=FILE:/run/starrocks-production-bootstrap.ccache

fail() {
  printf 'Production FreeIPA identity setup failed: %s\n' "$1" >&2
  exit 1
}

for file in "$admin_password_file" "$reader_password_file" "$writer_password_file"; do
  [[ -s "$file" && ! -L "$file" ]] || fail "a required protected credential is unavailable"
done
command -v ipa >/dev/null 2>&1 || fail "IPA CLI is unavailable"
command -v ldappasswd >/dev/null 2>&1 || fail "LDAP password utility is unavailable"
command -v kinit >/dev/null 2>&1 || fail "Kerberos client is unavailable"

cleanup() {
  KRB5CCNAME="$cache" kdestroy >/dev/null 2>&1 || true
  rm -f "$cache" "$temp_reader_password" "$temp_writer_password"
}
trap cleanup EXIT

if ! cat "$admin_password_file" | KRB5CCNAME="$cache" kinit "admin@${realm}" >/dev/null 2>&1; then
  fail "FreeIPA administrator authentication failed"
fi
export KRB5CCNAME="$cache"

ensure_group() {
  local name="$1"
  if ! ipa group-show "$name" >/dev/null 2>&1; then
    ipa group-add "$name" --desc="Lakehouse StarRocks role group" >/dev/null 2>&1 \
      || fail "role group creation failed"
  fi
}

ensure_user() {
  local name="$1" first="$2" last="$3"
  if ! ipa user-show "$name" >/dev/null 2>&1; then
    ipa user-add "$name" --first="$first" --last="$last" --random >/dev/null 2>&1 \
      || fail "user creation failed"
  fi
}

ensure_membership() {
  local group="$1" username="$2" state
  state="$(ipa group-show "$group" --all --raw 2>/dev/null)" \
    || fail "role group inspection failed"
  if grep -Fq "uid=${username}," <<<"$state"; then
    return 0
  fi
  ipa group-add-member "$group" "--users=${username}" >/dev/null 2>&1 \
    || fail "role membership assignment failed"
}

ensure_group lakehouse-developers
ensure_group lakehouse-analysts
ensure_group lakehouse-writers
ensure_user developer-user Developer User
ensure_user analyst-user Analyst User
ensure_user write-service-account Lakehouse Writer
ensure_user starrocks-ldap-reader StarRocks LDAPReader
ensure_membership lakehouse-developers developer-user
ensure_membership lakehouse-analysts analyst-user
ensure_membership lakehouse-writers write-service-account

# Secret files are newline-terminated; ldappasswd must receive the exact
# credential bytes without a final line terminator.
tr -d '\r\n' < "$reader_password_file" > "$temp_reader_password"
tr -d '\r\n' < "$writer_password_file" > "$temp_writer_password"
chmod 0600 "$temp_reader_password" "$temp_writer_password"
for target_dn in "$reader_dn" "$writer_dn"; do
  password_file="$temp_writer_password"
  [[ "$target_dn" != "$reader_dn" ]] || password_file="$temp_reader_password"
  ldappasswd -Y GSSAPI -H "ldaps://${FREEIPA_HOSTNAME:-ipa-prod.lakehouse.local}:636" \
    -T "$password_file" "$target_dn" >/dev/null 2>&1 \
    || fail "service identity password setup failed"
done

if ! ldapwhoami -x -H "ldaps://${FREEIPA_HOSTNAME:-ipa-prod.lakehouse.local}:636" \
  -D "$reader_dn" -y "$reader_password_file" >/dev/null 2>&1; then
  fail "read-only StarRocks LDAP bind verification failed"
fi

printf '%s\n' "Production StarRocks role groups and service identities are present; reader LDAPS bind verified."
