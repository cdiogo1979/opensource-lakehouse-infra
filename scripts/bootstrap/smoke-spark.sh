#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IMAGE="${SPARK_BOOTSTRAP_IMAGE:-local/lakehouse-spark-runtime:3.5.9_1.10.2}"
SECRET="$ROOT/.runtime/container-mounts/keycloak-writer-client-secret"
PASSWORD="$ROOT/.runtime/container-mounts/srv-default-writer-password"
APP="$ROOT/infra/spark-bootstrap/create_smoke_tables.py"

for required in "$SECRET" "$PASSWORD" "$APP"; do
  if [[ ! -f "$required" || -L "$required" || ! -r "$required" ]]; then
    echo "Required protected Spark bootstrap input is unavailable." >&2
    exit 1
  fi
done

docker image inspect "$IMAGE" >/dev/null 2>&1 || {
  echo "Required local Spark bootstrap image is unavailable: $IMAGE" >&2
  exit 1
}

docker run --rm \
  --network lakehouse-local_core \
  --mount "type=bind,src=$SECRET,dst=/run/secrets/keycloak-writer-client-secret,readonly" \
  --mount "type=bind,src=$PASSWORD,dst=/run/secrets/srv-default-writer-password,readonly" \
  --mount "type=bind,src=$APP,dst=/opt/lakehouse/create_smoke_tables.py,readonly" \
  --entrypoint /opt/spark/bin/spark-submit \
  "$IMAGE" /opt/lakehouse/create_smoke_tables.py
