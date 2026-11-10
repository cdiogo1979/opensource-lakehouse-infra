#!/usr/bin/env bash
# Remove a data product and all its artifacts (FR-11). The default product is refused.
#
#   scripts/operations/remove-data-product.sh <name> [--purge-data] [--yes] [--dry-run] [--no-restart]
#       [--admin-user USER] [--admin-password-file FILE]
#
# It lists the product's data and the members who lose access, and stops if any
# table, MV, or bucket object exists unless --purge-data is given. It asks for the
# product name to be typed (--yes skips that), backs up the file and state to
# .runtime/backups/, then removes the Jenkins folder (with its jobs and build
# history) and global entries, StarRocks roles and MV
# databases, Polaris roles and namespaces, RustFS buckets and policies, and the
# Keycloak groups and writer user. Users stay; only their memberships go. Every
# step is rerunnable, and the product file is deleted last.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
# shellcheck source=lib/data-products.sh
source scripts/operations/lib/data-products.sh

usage() {
  sed -n '3,5p' "$0" | sed 's/^# \{0,1\}//' >&2
  exit 2
}

name="" purge=false yes=false dry_run=false no_restart=false admin_user="platform-admin" admin_file=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --purge-data) purge=true; shift ;;
    --yes) yes=true; shift ;;
    --dry-run) dry_run=true; shift ;;
    --no-restart) no_restart=true; shift ;;
    --admin-user) [[ $# -ge 2 ]] || usage; admin_user="$2"; shift 2 ;;
    --admin-password-file) [[ $# -ge 2 ]] || usage; admin_file="$2"; shift 2 ;;
    -*) usage ;;
    *) [[ -z "$name" ]] || usage; name="$1"; shift ;;
  esac
done
[[ -n "$name" ]] || usage

file="$(python3 infra/products/product-cli.py resolve "$name")" || exit 2
take_lock
prepare_admin "$admin_user" "$admin_file"
product=(--product "$file")
dry=()
[[ "$dry_run" == true ]] && dry=(--dry-run)
purge_args=()
[[ "$purge" == true ]] && purge_args=(--purge-data)

step "Inventory of $name"
work="$(mktemp -d)"
trap 'rm -rf "$work"; release_lock' EXIT
python3 infra/keycloak/product-identity.py --inventory "${product[@]}" "${ADMIN_ARGS[@]}" > "$work/members.json"
python3 infra/polaris/bootstrap-catalogs.py --inventory "${product[@]}" > "$work/polaris.json"
python3 infra/rustfs/bootstrap-buckets.py --inventory "${product[@]}" > "$work/storage.json"
starrocks=()
if python3 -c 'import sys; sys.path.insert(0, "infra/starrocks"); import starrocks_common as sr; raise SystemExit(0 if sr.starrocks_enabled() else 1)'; then
  python3 infra/starrocks/bootstrap-starrocks.py --inventory "${product[@]}" > "$work/starrocks.json"
  starrocks=("$work/starrocks.json")
fi
rc=0
python3 infra/products/product-cli.py summarize "$name" "$work/members.json" "$work/polaris.json" "$work/storage.json" ${starrocks[@]+"${starrocks[@]}"} || rc=$?
if [[ "$rc" == 10 && "$purge" == false ]]; then
  die "$name still holds data; rerun with --purge-data to delete it with the product. Nothing was changed."
fi
[[ "$rc" == 0 || "$rc" == 10 ]] || die "the inventory could not be summarized."

if [[ "$dry_run" == false && "$yes" == false ]]; then
  [[ -t 0 ]] || die "confirmation needed: run interactively or pass --yes." 2
  printf 'Type the product name (%s) to remove it%s: ' "$name" "$([[ "$purge" == true ]] && echo ' and delete its data')"
  read -r answer
  [[ "$answer" == "$name" ]] || die "confirmation did not match; nothing was changed."
fi

if [[ "$dry_run" == false ]]; then
  step "Back up the product file and state"
  echo "Backup: $(python3 infra/products/product-cli.py backup "$name")"
fi
step "Jenkins: drop the product's folder, jobs, and entries"
apply_jenkins "$dry_run" "$no_restart" --exclude "$name"
step "StarRocks: MV databases and roles"
python3 infra/starrocks/bootstrap-starrocks.py --remove "${product[@]}" ${purge_args[@]+"${purge_args[@]}"} ${dry[@]+"${dry[@]}"}
step "Polaris: roles and grants, then tables, namespaces, and allowed locations"
python3 infra/polaris/bootstrap-product-authorization.py --remove "${product[@]}" ${dry[@]+"${dry[@]}"}
python3 infra/polaris/bootstrap-catalogs.py --remove "${product[@]}" ${purge_args[@]+"${purge_args[@]}"} ${dry[@]+"${dry[@]}"}
step "RustFS: buckets and policies"
python3 infra/rustfs/bootstrap-buckets.py --remove "${product[@]}" ${purge_args[@]+"${purge_args[@]}"} ${dry[@]+"${dry[@]}"}
python3 infra/rustfs/bootstrap-policies.py --remove "${product[@]}" ${dry[@]+"${dry[@]}"}
step "Keycloak: writer user, groups, and client roles"
python3 infra/keycloak/product-identity.py --remove "${product[@]}" ${dry[@]+"${dry[@]}"} "${ADMIN_ARGS[@]}"

if [[ "$dry_run" == true ]]; then
  step "Airflow: bundles and writers"
  apply_airflow true "$no_restart" --exclude "$name"
  echo
  echo "Dry run of the removal of $name completed; nothing was changed."
  exit 0
fi
step "Reconcile: former members lose their product roles"
python3 infra/polaris/reconcile-keycloak-groups.py
python3 infra/starrocks/reconcile-starrocks-users.py --transport docker
python3 infra/products/product-cli.py forget "$name"
step "Airflow: bundles and writers"
apply_airflow false "$no_restart"
echo
echo "Data product $name removed."
