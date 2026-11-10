#!/usr/bin/env bash
set -euo pipefail

# Run the token broker's behavioral tests inside its own image, which holds the
# pinned FastAPI/httpx the host Python lacks. Test tools go to a throwaway
# directory in the container; the repository is mounted read-only.
cd "$(dirname "$0")/../.."
image="${AIRFLOW_BROKER_IMAGE:-local/lakehouse-airflow-token-broker:1.0.0}"
docker run --rm --network bridge -v "$PWD:/src:ro" -w /src \
  -e PYTHONDONTWRITEBYTECODE=1 -e HOME=/tmp "$image" sh -c '
    pip install --quiet --disable-pip-version-check --target /tmp/deps pytest hypothesis pyyaml >/dev/null &&
    PYTHONPATH=/tmp/deps python -m pytest -q -p no:cacheprovider \
      tests/airflow/test_token_broker_writers.py "$@"' sh "$@"
