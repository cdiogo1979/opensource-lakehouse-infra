#!/usr/bin/env bash
set -euo pipefail
umask 077

# One-time bootstrap, run inside isolated FreeIPA after interactive `kinit admin`.
readonly provisioner_principal="lakehouse-membership/${FREEIPA_HOSTNAME:-ipa.lakehouse.local}"
readonly provisioner_keytab="/data/keytabs/lakehouse-membership.keytab"
readonly keytab_dir="/data/keytabs"
readonly realm="${KERBEROS_REALM:-LAKEHOUSE.LOCAL}"
readonly hive_principal="hive/${HIVE_SERVICE_FQDN:-hive-metastore.lakehouse.local}@${realm}"

fail() {
  printf 'FreeIPA bootstrap failed: %s\n' "$1" >&2
  exit 1
}

command -v ipa >/dev/null 2>&1 || fail "IPA CLI unavailable"
command -v ipa-getkeytab >/dev/null 2>&1 || fail "keytab utility unavailable"
klist -s || fail "obtain an administrator ticket first"

ensure_group() {
  local group="$1"
  if ipa group-show "$group" >/dev/null 2>&1; then
    return 0
  fi
  ipa group-add "$group" --desc="Lakehouse role group" >/dev/null 2>&1 || fail "role group creation failed"
}

ensure_user() {
  local username="$1" first="$2" last="$3"
  if ipa user-show "$username" >/dev/null 2>&1; then
    return 0
  fi
  # Do not generate or print passwords here. Unit 4 owns human account onboarding.
  ipa user-add "$username" --first="$first" --last="$last" >/dev/null 2>&1 \
    || fail "identity creation failed"
}

ensure_group lakehouse-developers
ensure_group lakehouse-analysts
ensure_group lakehouse-writers
ensure_user developer-user Developer User
ensure_user analyst-user Analyst User
ensure_user write-service-account Write Service
ensure_user starrocks StarRocks Service

ensure_group_member() {
  local group="$1" username="$2" group_state
  group_state="$(ipa group-show "$group" --all --raw 2>/dev/null)" \
    || fail "role group inspection failed"
  if grep -Fq "uid=${username}," <<<"${group_state}"; then
    return 0
  fi
  ipa group-add-member "$group" "--users=${username}" >/dev/null 2>&1 \
    || fail "role assignment failed"
}
ensure_group_member lakehouse-developers developer-user
ensure_group_member lakehouse-analysts analyst-user
ensure_group_member lakehouse-writers write-service-account

if ! ipa service-show "$provisioner_principal" >/dev/null 2>&1; then
  ipa service-add "$provisioner_principal" >/dev/null 2>&1 \
    || fail "scoped provisioner principal creation failed"
fi

for group in lakehouse-developers lakehouse-analysts lakehouse-writers; do
  permission="Lakehouse membership ${group}"
  if ! ipa permission-show "$permission" >/dev/null 2>&1; then
    ipa permission-add "$permission" --right=write --type=group \
      --attrs=member --targetgroup="$group" >/dev/null 2>&1 \
      || fail "scoped group permission creation failed"
  fi
  read_permission="Lakehouse membership read ${group}"
  if ! ipa permission-show "$read_permission" >/dev/null 2>&1; then
    ipa permission-add "$read_permission" --right=read --right=search --type=group \
      --attrs=cn --attrs=member --targetgroup="$group" >/dev/null 2>&1 \
      || fail "scoped group read permission creation failed"
  fi
done

if ! ipa privilege-show "Lakehouse role membership" >/dev/null 2>&1; then
  ipa privilege-add "Lakehouse role membership" >/dev/null 2>&1 \
    || fail "scoped privilege creation failed"
fi
for group in lakehouse-developers lakehouse-analysts lakehouse-writers; do
  ipa privilege-add-permission "Lakehouse role membership" \
    --permissions="Lakehouse membership ${group}" >/dev/null 2>&1 || {
      privilege_state="$(ipa privilege-show "Lakehouse role membership" --all --raw 2>/dev/null)" \
        || fail "scoped privilege inspection failed"
      grep -Fq "Lakehouse membership ${group}" <<<"${privilege_state}" \
        || fail "scoped permission attachment failed"
    }
  ipa privilege-add-permission "Lakehouse role membership" \
    --permissions="Lakehouse membership read ${group}" >/dev/null 2>&1 || {
      privilege_state="$(ipa privilege-show "Lakehouse role membership" --all --raw 2>/dev/null)" \
        || fail "scoped privilege inspection failed"
      grep -Fq "Lakehouse membership read ${group}" <<<"${privilege_state}" \
        || fail "scoped read permission attachment failed"
    }
done
if ! ipa role-show "Lakehouse Membership Manager" >/dev/null 2>&1; then
  ipa role-add "Lakehouse Membership Manager" >/dev/null 2>&1 \
    || fail "scoped role creation failed"
fi
ipa role-add-privilege "Lakehouse Membership Manager" \
  --privileges="Lakehouse role membership" >/dev/null 2>&1 || {
    role_state="$(ipa role-show "Lakehouse Membership Manager" --all --raw 2>/dev/null)" \
      || fail "scoped role inspection failed"
    grep -Fq "Lakehouse role membership" <<<"${role_state}" \
      || fail "scoped privilege attachment failed"
  }

if ! ipa service-show "$provisioner_principal" >/dev/null 2>&1; then
  ipa service-add --force "$provisioner_principal" >/dev/null 2>&1 \
    || fail "dedicated membership service principal creation failed"
fi

# Older bootstrap revisions accidentally attached FreeIPA's own HTTP server
# principal to the membership role. Remove only that stale role membership.
legacy_http_principal="HTTP/${FREEIPA_HOSTNAME:-ipa.lakehouse.local}"
role_state="$(ipa role-show "Lakehouse Membership Manager" --all --raw 2>/dev/null)" \
  || fail "scoped role inspection failed"
if grep -Fq "krbprincipalname=${legacy_http_principal}@${realm}" <<<"${role_state}"; then
  ipa role-remove-member "Lakehouse Membership Manager" \
    "--services=${legacy_http_principal}" >/dev/null 2>&1 \
    || fail "stale HTTP role membership removal failed"
fi

ensure_keytab() {
  local principal="$1" filename="$2" destination="${keytab_dir}/$2"
  if [[ -s "$destination" ]]; then
    klist -k "$destination" 2>/dev/null | grep -Fq "$principal" \
      || fail "existing keytab principal does not match its assignment"
    return 0
  fi
  local temporary="${destination}.tmp"
  rm -f "$temporary"
  ipa-getkeytab -p "$principal" -k "$temporary" >/dev/null 2>&1 \
    || fail "service keytab issuance failed"
  chmod 600 "$temporary"
  mv "$temporary" "$destination"
}

mkdir -p "$keytab_dir"
chmod 700 "$keytab_dir"
if ! ipa service-show "$hive_principal" >/dev/null 2>&1; then
  ipa host-show "${HIVE_SERVICE_FQDN:-hive-metastore.lakehouse.local}" >/dev/null 2>&1 \
    || ipa host-add --force "${HIVE_SERVICE_FQDN:-hive-metastore.lakehouse.local}" \
      >/dev/null 2>&1 || fail "Hive service host registration failed"
  # The FreeIPA container's Docker DNS resolver may not resolve this internal
  # service hostname even though its host object is registered in IPA.
  ipa service-add --force "$hive_principal" >/dev/null 2>&1 \
    || fail "Hive service principal creation failed"
fi
ensure_keytab "$hive_principal" hive-metastore.keytab
ensure_keytab "write-service-account@${realm}" write-service-account.keytab
ensure_keytab "starrocks@${realm}" starrocks.keytab
ipa role-add-member "Lakehouse Membership Manager" \
  --services="$provisioner_principal" >/dev/null 2>&1 || {
    role_state="$(ipa role-show "Lakehouse Membership Manager" --all --raw 2>/dev/null)" \
      || fail "scoped role inspection failed"
    grep -Fq "$provisioner_principal" <<<"${role_state}" \
      || fail "provisioner role assignment failed"
  }

# ipa-getkeytab creates a new key only when the protected file is absent.
# Never overwrite it on rerun because that would invalidate the current key.
if [[ ! -s "$provisioner_keytab" ]]; then
  temporary_keytab="${provisioner_keytab}.tmp"
  rm -f "$temporary_keytab"
  ipa-getkeytab -p "$provisioner_principal" -k "$temporary_keytab" \
    >/dev/null 2>&1 || fail "scoped provisioner keytab issuance failed"
  chmod 600 "$temporary_keytab"
  mv "$temporary_keytab" "$provisioner_keytab"
fi
chmod 600 "$provisioner_keytab"

printf '%s\n' "FreeIPA base groups and identities are ready."
printf '%s\n' "Scoped membership credential is stored in protected FreeIPA state (not displayed)."
printf '%s\n' "Human password setup and active service cutover remain separate workflows."
