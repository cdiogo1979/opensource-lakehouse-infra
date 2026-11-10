#!/usr/bin/env bash
# Check that the Spark runtime and Jupyter images hold the same workload Python environment:
# each /opt/lakehouse/venv is Python 3.10 with exactly infra/workload-python/requirements.lock,
# both embedded locks equal the workspace lock, both pip freeze outputs are identical, and
# Jupyter offers the one "Lakehouse (Python 3.10)" kernel. Build both images first.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOCK="$ROOT_DIR/infra/workload-python/requirements.lock"
RUNTIME_IMAGE="${LAKEHOUSE_SPARK_IMAGE:-local/lakehouse-spark-runtime:3.5.5_1.10.2}"
JUPYTER_IMAGE="${LAKEHOUSE_JUPYTER_IMAGE:-local/lakehouse-jupyter-singleuser:6.1.1-spark}"
VENV_PYTHON=/opt/lakehouse/venv/bin/python

work="$(mktemp -d)"
trap 'rm -rf -- "$work"' EXIT
failures=0

check_image() {
  local label="$1" image="$2"
  echo "== $label ($image)"
  if ! docker run --rm --entrypoint "$VENV_PYTHON" "$image" /opt/lakehouse/workload_python.py \
      check-venv "$VENV_PYTHON" --lock /opt/lakehouse/requirements.lock; then
    failures=$((failures + 1))
  fi
  docker run --rm --entrypoint cat "$image" /opt/lakehouse/requirements.lock > "$work/$label.lock"
  if ! cmp -s "$LOCK" "$work/$label.lock"; then
    echo "FAIL: the image's /opt/lakehouse/requirements.lock differs from infra/workload-python/requirements.lock (rebuild the image)."
    failures=$((failures + 1))
  fi
  docker run --rm --entrypoint env "$image" -u PYTHONPATH "$VENV_PYTHON" -m pip freeze --disable-pip-version-check > "$work/$label.freeze"
}

check_image runtime "$RUNTIME_IMAGE"
check_image jupyter "$JUPYTER_IMAGE"

if diff -u "$work/runtime.freeze" "$work/jupyter.freeze"; then
  echo "OK: both venvs report the same $(wc -l < "$work/runtime.freeze" | tr -d ' ') packages."
else
  echo "FAIL: the two venvs differ (above)."
  failures=$((failures + 1))
fi

echo "== Jupyter kernels"
if ! docker run --rm --entrypoint python "$JUPYTER_IMAGE" -c '
import sys
from pathlib import Path
from jupyter_client.kernelspec import KernelSpecManager
specs = KernelSpecManager(ensure_native_kernel=False).get_all_specs()
spec = specs.get("python3", {}).get("spec", {})
problems = []
if sorted(specs) != ["python3"]:
    problems.append(f"kernels {sorted(specs)}, expected only python3")
if spec.get("display_name") != "Lakehouse (Python 3.10)" or spec.get("argv", [""])[0] != "/opt/lakehouse/venv/bin/python":
    problems.append("python3 is not the Lakehouse (Python 3.10) kernel on /opt/lakehouse/venv")
if not Path("/etc/jupyter/jupyter_server_config.d/lakehouse-kernels.json").is_file():
    problems.append("the server setting that hides the native kernel is missing")
print("\n".join(problems) or "OK: one kernel, Lakehouse (Python 3.10)")
sys.exit(1 if problems else 0)
'; then
  failures=$((failures + 1))
fi

if [[ "$failures" -ne 0 ]]; then
  echo "Workload Python parity: $failures check(s) failed."
  exit 1
fi
echo "Workload Python parity: OK."
