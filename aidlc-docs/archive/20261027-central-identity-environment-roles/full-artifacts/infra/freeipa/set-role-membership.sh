#!/usr/bin/env bash
set -euo pipefail
umask 077

if [[ $# -ne 3 ]]; then
  echo "Usage: set-role-membership.sh USER GROUP add|remove" >&2
  exit 2
fi

readonly username="$1"
readonly group="$2"
readonly action="$3"
readonly provisioner_principal="lakehouse-membership/${FREEIPA_HOSTNAME:-ipa.lakehouse.local}"
readonly keytab="/data/keytabs/lakehouse-membership.keytab"
readonly cache="FILE:/run/lakehouse-membership.ccache"

if [[ ! "$username" =~ ^[A-Za-z][A-Za-z0-9_.-]{0,31}$ ]]; then
  echo "Invalid identity name." >&2
  exit 2
fi
case "$group" in
  lakehouse-developers|lakehouse-analysts|lakehouse-writers) ;;
  *) echo "Unsupported role group." >&2; exit 2 ;;
esac
case "$action" in
  add|remove) ;;
  *) echo "Action must be add or remove." >&2; exit 2 ;;
esac

[[ -s "$keytab" ]] || { echo "Scoped FreeIPA credential is unavailable." >&2; exit 1; }
command -v timeout >/dev/null 2>&1 || { echo "Required timeout utility is unavailable." >&2; exit 1; }
command -v ipa >/dev/null 2>&1 || { echo "IPA CLI is unavailable." >&2; exit 1; }

export KRB5CCNAME="$cache"
cleanup() {
  KRB5CCNAME="$cache" kdestroy >/dev/null 2>&1 || true
  rm -f /run/lakehouse-membership.ccache
}
trap cleanup EXIT

if ! timeout 10s kinit -kt "$keytab" "$provisioner_principal" >/dev/null 2>&1; then
  echo "Scoped FreeIPA authentication failed." >&2
  exit 1
fi

membership_exists() {
  local state
  state="$(timeout 10s ipa group-show "$group" --all --raw 2>/dev/null)" || return 2
  grep -Fq "uid=${username}," <<<"${state}"
}

case "$action" in
  add)
    if membership_exists; then
      printf '%s\n' "Membership is already present."
      exit 0
    else
      result=$?
      if [[ $result -ne 1 ]]; then
        echo "Could not inspect the requested role group." >&2
        exit 1
      fi
    fi
    if ! timeout 15s ipa group-add-member "$group" "--users=$username" >/dev/null 2>&1; then
      echo "FreeIPA membership add failed; verify account and scoped permission." >&2
      exit 1
    fi
    membership_exists || { echo "FreeIPA did not confirm the membership add." >&2; exit 1; }
    ;;
  remove)
    if membership_exists; then
      :
    else
      result=$?
      if [[ $result -eq 1 ]]; then
        printf '%s\n' "Membership is already absent."
        exit 0
      fi
      echo "Could not inspect the requested role group." >&2
      exit 1
    fi
    if ! timeout 15s ipa group-remove-member "$group" "--users=$username" >/dev/null 2>&1; then
      echo "FreeIPA membership removal failed; verify account and scoped permission." >&2
      exit 1
    fi
    if membership_exists; then
      echo "FreeIPA still reports the membership after removal." >&2
      exit 1
    else
      result=$?
      [[ $result -eq 1 ]] || { echo "Could not verify membership removal." >&2; exit 1; }
    fi
    ;;
esac
printf 'Membership %s completed for %s in %s.\n' "$action" "$username" "$group"
