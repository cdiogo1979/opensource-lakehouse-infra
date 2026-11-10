#!/usr/bin/env bash
set -euo pipefail

readonly username="rustfs-reconciler"

fail() {
  printf 'FreeIPA read-only identity setup failed: %s\n' "$1" >&2
  exit 1
}

command -v ipa >/dev/null 2>&1 || fail "IPA CLI unavailable"
klist -s || fail "obtain an administrator ticket interactively first"

set +e
lookup_output="$(ipa user-show "$username" 2>&1)"
lookup_status=$?
set -e
if [[ "${lookup_status}" -eq 0 ]]; then
  printf 'FreeIPA read-only identity already exists; no change made.\n'
  exit 0
fi
if ! grep -Eiq 'user not found|no such entry' <<<"${lookup_output}"; then
  fail "identity inspection failed"
fi
unset lookup_output

# The CLI prompts on the terminal for the initial password. Do not pass or log
# its value through arguments, environment variables, or command output.
ipa user-add "$username" --first=RustFS --last=Reconciler --password \
  >/dev/null 2>&1 || fail "user creation failed"
printf 'Created the dedicated FreeIPA directory query identity.\n'
