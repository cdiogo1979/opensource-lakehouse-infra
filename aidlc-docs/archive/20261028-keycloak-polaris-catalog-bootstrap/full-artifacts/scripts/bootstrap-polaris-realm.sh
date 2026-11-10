#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$ROOT/.runtime/container-mounts/polaris-application.properties"
CREDENTIALS="$ROOT/.runtime/container-mounts/polaris-bootstrap-credentials"

for required in "$CONFIG" "$CREDENTIALS"; do
  if [[ ! -f "$required" || -L "$required" || ! -r "$required" ]]; then
    echo "Required protected Polaris bootstrap file is unavailable." >&2
    exit 1
  fi
done

echo "Bootstrapping the Polaris lakehouse realm (credential values omitted)."
docker run --rm \
  --network lakehouse-local_core \
  --env QUARKUS_CONFIG_LOCATIONS=/deployment/config/application.properties \
  --mount "type=bind,src=$CONFIG,dst=/deployment/config/application.properties,readonly" \
  --mount "type=bind,src=$CREDENTIALS,dst=/run/secrets/polaris-bootstrap-credentials,readonly" \
  apache/polaris-admin-tool:1.8.0 \
  bootstrap --credentials-file /run/secrets/polaris-bootstrap-credentials
