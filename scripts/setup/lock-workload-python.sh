#!/usr/bin/env bash
# Regenerate infra/workload-python/requirements.lock from requirements.in, in the Spark
# runtime's base image: the same Python 3.10, architecture and glibc as the runtime.
# Rebuild both images afterwards, then run scripts/verify/workload-python-parity.sh.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOCK_DIR="$ROOT_DIR/infra/workload-python"
BASE_IMAGE="$(sed -n 's|^FROM \(apache/spark:[^ ]*\).*|\1|p' "$ROOT_DIR/infra/spark-runtime/Dockerfile")"
if [[ -z "$BASE_IMAGE" ]]; then
  echo "ERROR: the Spark runtime's base image was not found in infra/spark-runtime/Dockerfile." >&2
  exit 1
fi

work="$(mktemp -d)"
trap 'rm -rf -- "$work"' EXIT

# As root, with venv support added as in the runtime image (the base's Python 3.10 has no ensurepip).
docker run --rm --user root -v "$LOCK_DIR:/work:ro" --entrypoint bash "$BASE_IMAGE" -c '
set -euo pipefail
apt-get update -qq >/dev/null && apt-get install --yes --no-install-recommends -qq python3.10-venv >/dev/null
python3 -m venv /tmp/venv
/tmp/venv/bin/pip install --quiet --disable-pip-version-check --no-input --no-cache-dir \
  --only-binary=:all: --requirement /work/requirements.in
env -u PYTHONPATH /tmp/venv/bin/pip freeze --disable-pip-version-check
' > "$work/freeze.txt"

{
  python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import workload_python; print(workload_python.LOCK_HEADER)' "$LOCK_DIR"
  cat "$work/freeze.txt"
} > "$work/requirements.lock"
python3 "$LOCK_DIR/workload_python.py" check-lock "$work/requirements.lock"
cp "$work/requirements.lock" "$LOCK_DIR/requirements.lock"
echo "Wrote infra/workload-python/requirements.lock ($(grep -vc '^#' "$LOCK_DIR/requirements.lock") packages)."
