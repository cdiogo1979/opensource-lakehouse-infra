#!/usr/bin/env bash
set -euo pipefail
umask 077

readonly secret_dir="${RANGER_TEST_SECRET_DIR:-.runtime/ranger-test/secrets}"
readonly names=(
  ranger-db-root-password
  ranger-db-service-password
  ranger-admin-password
  ranger-tagsync-password
  ranger-usersync-password
  ranger-keyadmin-password
  ranger-ipa-admin-password
  ranger-ipa-directory-manager-password
  ranger-usersync-bind-password
  ranger-test-user-password
)

file_mode() {
  stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1"
}

mkdir -p "$secret_dir"
chmod 0700 "$secret_dir"
for name in "${names[@]}"; do
  path="$secret_dir/$name"
  if [[ -e "$path" ]]; then
    if [[ ! -f "$path" || ! -s "$path" || "$(file_mode "$path")" != 600 ]]; then
      echo "Refusing to reuse an existing Ranger test secret with unexpected type, size, or permissions: $name" >&2
      exit 1
    fi
    case "$name" in
      ranger-admin-password|ranger-tagsync-password|ranger-usersync-password|ranger-keyadmin-password|ranger-ipa-admin-password|ranger-ipa-directory-manager-password|ranger-usersync-bind-password|ranger-test-user-password)
        if ! grep -Eq '^R[a-f0-9]{64}a9$' "$path"; then
          echo "Refusing to reuse an existing Ranger account secret that does not meet the test password policy: $name" >&2
          exit 1
        fi
        ;;
      *)
        if ! grep -Eq '^[a-f0-9]{64}$' "$path"; then
          echo "Refusing to reuse an existing Ranger database secret with an unexpected generated format: $name" >&2
          exit 1
        fi
        ;;
    esac
    continue
  fi
  case "$name" in
    ranger-admin-password|ranger-tagsync-password|ranger-usersync-password|ranger-keyadmin-password|ranger-ipa-admin-password|ranger-ipa-directory-manager-password|ranger-usersync-bind-password|ranger-test-user-password)
      printf 'R%sa9\n' "$(openssl rand -hex 32)" > "$path"
      ;;
    *)
      openssl rand -hex 32 > "$path"
      ;;
  esac
  chmod 0600 "$path"
done

ipa_options="$secret_dir/freeipa-test-install-options"
if [[ ! -e "$ipa_options" ]]; then
  {
    printf '%s\n' '--unattended'
    printf '%s\n' '--realm=LAKEHOUSE.TEST'
    printf '%s\n' '--domain=ranger-test.lakehouse.test'
    printf '%s\n' '--hostname=ipa.ranger-test.lakehouse.test'
    printf '%s\n' '--ip-address=172.29.252.10'
    printf '%s\n' '--no-ntp' '--no-ssh' '--no-sshd'
    printf '%s\n' '--skip-mem-check'
    printf '%s%s\n' '--admin-password=' "$(cat "$secret_dir/ranger-ipa-admin-password")"
    printf '%s%s\n' '--ds-password=' "$(cat "$secret_dir/ranger-ipa-directory-manager-password")"
  } > "$ipa_options"
  chmod 0600 "$ipa_options"
elif [[ ! -f "$ipa_options" || ! -s "$ipa_options" || "$(file_mode "$ipa_options")" != 600 ]]; then
  echo "Refusing to reuse FreeIPA test install options with unexpected type, size, or permissions." >&2
  exit 1
fi

# Older generated options included an unsupported, ambiguous FreeIPA flag.
# FreeIPA does not enable integrated DNS unless --setup-dns is requested.
if grep -Eq '^--no-(dns|firewalld)$|^--ip-address=172\.31\.252\.10$' "$ipa_options" || ! grep -Fxq -- '--skip-mem-check' "$ipa_options"; then
  python3 - "$ipa_options" <<'PY'
import os
import sys
import tempfile
from pathlib import Path

path = Path(sys.argv[1])
lines = path.read_text().splitlines(keepends=True)
updated = []
for line in lines:
    option = line.rstrip("\r\n")
    if option in {"--no-dns", "--no-firewalld"}:
        continue
    if option == "--ip-address=172.31.252.10":
        line = "--ip-address=172.29.252.10" + ("\n" if line.endswith("\n") else "")
    updated.append(line)
if not any(line.rstrip("\r\n") == "--skip-mem-check" for line in updated):
    updated.append("--skip-mem-check\n")
fd, temp_name = tempfile.mkstemp(prefix=".freeipa-options-", dir=path.parent)
try:
    with os.fdopen(fd, "w") as stream:
        stream.writelines(updated)
    os.chmod(temp_name, 0o600)
    os.replace(temp_name, path)
finally:
    if os.path.exists(temp_name):
        os.unlink(temp_name)
PY
fi

ipa_ca="$secret_dir/freeipa-test-ca.crt"
if [[ ! -e "$ipa_ca" ]]; then
  : > "$ipa_ca"
  chmod 0600 "$ipa_ca"
fi
if [[ ! -f "$ipa_ca" || "$(file_mode "$ipa_ca")" != 600 ]]; then
  echo "Refusing to reuse the FreeIPA test CA path with unexpected type or permissions." >&2
  exit 1
fi
echo "Prepared missing Ranger test secret files under $secret_dir; values were not displayed."
