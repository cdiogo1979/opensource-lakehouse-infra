#!/usr/bin/env bash
# Create a lakehouse realm user with no groups (FR-9); assign groups in Keycloak.
#
#   scripts/operations/create-user.sh <username> [--email E] [--first-name F] [--last-name L]
#       [--password-file FILE] [--admin-user USER] [--admin-password-file FILE]
#
# The new user's password is the first line of --password-file, or ChangeM3!
# (permanent). The script signs in as the given platform administrator (password
# from --admin-password-file, LAKEHOUSE_ADMIN_PASSWORD, or a hidden prompt).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
exec python3 infra/keycloak/create-user.py "$@"
