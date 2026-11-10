#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# With the containerd image store, BuildKit adds a timestamped provenance attestation
# to every build, giving cached builds a new image ID and making Compose recreate
# running containers on every start. Builds here are local, so leave it out.
export BUILDX_NO_DEFAULT_ATTESTATIONS=1
# Each command passes only the enabled module files, so Compose would report the
# other modules' containers as orphans and suggest --remove-orphans, which would
# delete them. The modules are deliberately separate files of one project.
export COMPOSE_IGNORE_ORPHANS=true

# Every step below covers every data product file (data-products/*.yaml,
# default first), so a reset and rebuild recreate all products.
scripts/lakehouse.sh start
python3 infra/keycloak/bootstrap-realm.py
scripts/bootstrap/bootstrap-users.sh
bash scripts/bootstrap/bootstrap-polaris-realm.sh
python3 infra/rustfs/bootstrap-buckets.py
python3 infra/rustfs/bootstrap-policies.py
python3 infra/polaris/bootstrap-catalogs.py
python3 infra/polaris/bootstrap-product-authorization.py
python3 infra/polaris/reconcile-keycloak-groups.py
docker compose -f compose.core.yml --profile scheduled-reconciliation up -d --build polaris-group-reconciler
python3 scripts/verify/polaris-keycloak-auth.py
scripts/bootstrap/smoke-spark.sh
python3 infra/starrocks/bootstrap-starrocks.py
python3 infra/starrocks/reconcile-starrocks-users.py --transport docker

python3 infra/products/product-cli.py record --all

echo "Data product bootstrap and smoke verification completed."
