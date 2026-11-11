#!/usr/bin/env bash
set -euo pipefail

# Run the platform DAG factory's Airflow-side tests inside the Airflow image, which
# holds Airflow and the Docker SDK the host Python lacks. Test tools go to a
# throwaway directory in the container; the repository is mounted read-only.
cd "$(dirname "$0")/../.."
image="${AIRFLOW_IMAGE:-local/lakehouse-airflow:3.3.2}"
docker run --rm --network bridge --entrypoint sh -v "$PWD:/src:ro" -w /src \
  -e PYTHONDONTWRITEBYTECODE=1 -e HOME=/tmp -e AIRFLOW__CORE__LOAD_EXAMPLES=False "$image" -c '
    pip install --quiet --disable-pip-version-check --target /tmp/deps pytest hypothesis >/dev/null &&
    PYTHONPATH=/tmp/deps:/src/infra/airflow python -m pytest -q -p no:cacheprovider \
      tests/airflow/test_dag_factory.py tests/airflow/test_workflow_spec.py tests/airflow/test_mv_promotion.py tests/airflow/test_task_args.py "$@"' sh "$@"
