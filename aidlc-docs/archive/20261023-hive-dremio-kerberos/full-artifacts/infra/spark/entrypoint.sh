#!/bin/bash
set -euo pipefail

mkdir -p /tmp/spark-events
start-master.sh -p 7077
start-worker.sh spark://spark-iceberg:7077
start-history-server.sh

if [[ $# -gt 0 ]]; then
  exec "$@"
fi

exec notebook
