#!/usr/bin/env bash
# Reset the bootstrap users (joe-developer, peter-analyst, maria-owner,
# srv-default-writer, platform-admin) to the default password and their default group.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 infra/keycloak/bootstrap-users.py "$@"
