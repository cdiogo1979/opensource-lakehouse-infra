#!/usr/bin/env bash
set -euo pipefail

readonly options_secret="/run/secrets/freeipa-server-install-options"
readonly options_link="/data/ipa-server-install-options"

if [[ ! -s "${options_secret}" ]]; then
  echo "FreeIPA installer-options secret is missing or empty." >&2
  exit 2
fi

if [[ ! -e "${options_link}" && ! -L "${options_link}" ]]; then
  ln -s "${options_secret}" "${options_link}"
fi

if [[ ! -s "${options_link}" ]]; then
  echo "FreeIPA installer-options link does not resolve to a non-empty secret." >&2
  exit 2
fi

exec /usr/local/sbin/init "$@"
