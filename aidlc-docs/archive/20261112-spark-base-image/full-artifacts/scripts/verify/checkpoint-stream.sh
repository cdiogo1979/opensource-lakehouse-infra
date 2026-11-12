#!/usr/bin/env bash
set -euo pipefail

# Iceberg streaming with an s3ckpt:// checkpoint, in two separate Spark sessions: the second
# resumes with no reprocessing; a checkpoint in another bucket fails without its key.
# Needs the stack started, the default product bootstrapped and the runtime image built.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IMAGE="${SPARK_BOOTSTRAP_IMAGE:-local/lakehouse-spark-runtime:3.5.9_1.10.2}"
SECRET="$ROOT/.runtime/container-mounts/keycloak-writer-client-secret"
PASSWORD="$ROOT/.runtime/container-mounts/srv-default-writer-password"
KEY="$ROOT/.runtime/container-mounts/checkpoint-keys/bucket-default-dev"

for required in "$SECRET" "$PASSWORD" "$KEY"; do
  if [[ ! -f "$required" || -L "$required" || ! -r "$required" ]]; then
    echo "Required protected input is unavailable: $(basename "$required")" >&2
    exit 1
  fi
done

run_id="$(date -u +%Y%m%d%H%M%S)-$RANDOM"
log="$(mktemp)"
trap 'rm -f "$log"' EXIT
for phase in first resume; do
  status=0
  docker run --rm \
    --network lakehouse-local_core \
    --mount "type=bind,src=$SECRET,dst=/run/secrets/keycloak-writer-client-secret,readonly" \
    --mount "type=bind,src=$PASSWORD,dst=/run/secrets/srv-default-writer-password,readonly" \
    --mount "type=bind,src=$KEY,dst=/run/secrets/lakehouse-checkpoints/bucket-default-dev,readonly" \
    --mount "type=bind,src=$ROOT/infra/spark-bootstrap,dst=/opt/lakehouse/bootstrap,readonly" \
    --env PYTHONPATH=/opt/lakehouse/bootstrap \
    --entrypoint /opt/spark/bin/spark-submit \
    "$IMAGE" /opt/lakehouse/bootstrap/verify_checkpoint_stream.py "$phase" "$run_id" >"$log" 2>&1 || status=$?
  # Only the verdict lines and exception headlines; Spark logs stay out of the terminal.
  grep -E '^(OK|FAIL)|^[A-Za-z.]*(Exception|Error):' "$log" | head -20 || true
  if [[ "${status:-0}" -ne 0 ]]; then
    echo "Checkpoint stream verification failed in the $phase phase." >&2
    exit 1
  fi
done
echo "Checkpoint stream verification passed."
