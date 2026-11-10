#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

scripts/lakehouse.sh start
python3 infra/keycloak/bootstrap-realm.py
bash scripts/bootstrap-polaris-realm.sh
python3 infra/rustfs/bootstrap-buckets.py
python3 infra/polaris/bootstrap-default-catalogs.py
python3 infra/polaris/bootstrap-product-authorization.py
python3 infra/polaris/reconcile-keycloak-groups.py
docker compose --profile scheduled-reconciliation up -d --build polaris-group-reconciler
python3 scripts/verify-polaris-keycloak-auth.py
scripts/run-bootstrap-smoke-spark.sh

echo "Default product bootstrap and smoke verification completed."
