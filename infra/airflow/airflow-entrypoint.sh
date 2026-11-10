#!/usr/bin/env bash
set -euo pipefail

python /opt/airflow/scripts/validate-bundle-config.py

exec /entrypoint "$@"
