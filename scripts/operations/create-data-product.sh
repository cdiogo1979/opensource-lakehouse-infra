#!/usr/bin/env bash
# Create or apply a data product from its configuration file (FR-2).
#
#   scripts/operations/create-data-product.sh --init <name>
#   scripts/operations/create-data-product.sh data-products/<name>.yaml [--dry-run] [--no-restart]
#       [--admin-user USER] [--admin-password-file FILE]
#
# --init writes the standard file to review or edit. Applying a file creates what
# is missing and converges grants to it in every component: Keycloak (as the given
# platform administrator), RustFS, Polaris, StarRocks, Jenkins (the product's
# folder, its permissions, and, with a repo, the <name>_ci and <name>_cd jobs),
# and Airflow.
# Rerunning after an edit applies the change, revokes included. Names are locked
# once applied. The admin password comes from --admin-password-file, then
# LAKEHOUSE_ADMIN_PASSWORD, then a hidden prompt; it is never an argument.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
# shellcheck source=lib/data-products.sh
source scripts/operations/lib/data-products.sh

usage() {
  sed -n '3,6p' "$0" | sed 's/^# \{0,1\}//' >&2
  exit 2
}

[[ $# -ge 1 ]] || usage
if [[ "$1" == "--init" ]]; then
  [[ $# -eq 2 ]] || usage
  exec python3 infra/products/product-cli.py init "$2"
fi

file="" dry_run=false no_restart=false admin_user="platform-admin" admin_file=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) dry_run=true; shift ;;
    --no-restart) no_restart=true; shift ;;
    --admin-user) [[ $# -ge 2 ]] || usage; admin_user="$2"; shift 2 ;;
    --admin-password-file) [[ $# -ge 2 ]] || usage; admin_file="$2"; shift 2 ;;
    -*) usage ;;
    *) [[ -z "$file" ]] || usage; file="$1"; shift ;;
  esac
done
[[ -n "$file" ]] || usage

take_lock
step "Validate $file"
python3 infra/products/product-cli.py validate "$file"
name="$(basename "$file" .yaml)"
prepare_admin "$admin_user" "$admin_file"
dry=()
[[ "$dry_run" == true ]] && dry=(--dry-run)
product=(--product "$file")

step "Keycloak: groups, client roles, platform-admin owner role, writer user"
python3 infra/keycloak/product-identity.py "${product[@]}" ${dry[@]+"${dry[@]}"} "${ADMIN_ARGS[@]}"
step "RustFS: buckets and policies"
python3 infra/rustfs/bootstrap-buckets.py "${product[@]}" ${dry[@]+"${dry[@]}"}
python3 infra/rustfs/bootstrap-policies.py "${product[@]}" ${dry[@]+"${dry[@]}"}
step "Polaris: allowed locations, namespaces, roles, namespace-scoped grants"
python3 infra/polaris/bootstrap-catalogs.py "${product[@]}" ${dry[@]+"${dry[@]}"}
python3 infra/polaris/bootstrap-product-authorization.py "${product[@]}" ${dry[@]+"${dry[@]}"}
if [[ "$dry_run" == false ]]; then
  python3 infra/polaris/reconcile-keycloak-groups.py
fi
step "StarRocks: roles, database-scoped grants, MV databases"
python3 infra/starrocks/bootstrap-starrocks.py "${product[@]}" --skip-smoke ${dry[@]+"${dry[@]}"}
if [[ "$dry_run" == false ]]; then
  python3 infra/starrocks/reconcile-starrocks-users.py --transport docker
fi
step "Jenkins: folder, permissions, and jobs"
apply_jenkins "$dry_run" "$no_restart"

if [[ "$dry_run" == true ]]; then
  step "Airflow: bundles and writers"
  apply_airflow true "$no_restart"
  echo
  echo "Dry run of $name completed; nothing was changed."
  exit 0
fi
python3 infra/products/product-cli.py record "$file"
step "Airflow: bundles and writers"
apply_airflow false "$no_restart"
echo
echo "Data product $name applied. JupyterHub and Airflow pick up its groups at the next sign-in."
echo "Next: add people to its groups in the Keycloak admin console (http://keycloak.localhost:8080/admin/lakehouse/console/)."
