# Shared helpers for the data product operator scripts (bash 3.2 compatible).
# Sourced, not executed. Expects ROOT to be the repository root.

STATE_DIR="$ROOT/.runtime/state/data-products"
LOCK_DIR="$STATE_DIR/.lock"
ADMIN_ARGS=()
OWN_PASSWORD=false

die() { echo "ERROR: $*" >&2; exit "${2:-1}"; }

# One apply or remove at a time (BR-10); a stale lock is reported, never removed.
take_lock() {
  mkdir -p "$STATE_DIR"
  chmod 700 "$STATE_DIR"
  if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    die "another data product operation holds $LOCK_DIR; if none is running, remove that directory and retry."
  fi
  trap 'release_lock' EXIT
}

release_lock() {
  rmdir "$LOCK_DIR" 2>/dev/null || true
  if [[ "$OWN_PASSWORD" == true ]]; then unset LAKEHOUSE_ADMIN_PASSWORD; fi
}

# --admin-user / --admin-password-file are passed to the Keycloak steps. Without a
# file or LAKEHOUSE_ADMIN_PASSWORD, the password is prompted once without echo and
# exported to the child steps only (never placed in arguments).
prepare_admin() {
  local user="$1" file="$2"
  ADMIN_ARGS=(--admin-user "$user")
  if [[ -n "$file" ]]; then
    [[ -f "$file" && ! -L "$file" ]] || die "the admin password file is unavailable." 2
    ADMIN_ARGS+=(--admin-password-file "$file")
  elif [[ -z "${LAKEHOUSE_ADMIN_PASSWORD:-}" ]]; then
    [[ -t 0 ]] || die "no admin password: pass --admin-password-file or set LAKEHOUSE_ADMIN_PASSWORD." 2
    local password=""
    printf 'Keycloak password for %s: ' "$user" >&2
    read -r -s password
    echo >&2
    [[ -n "$password" ]] || die "empty admin password." 2
    export LAKEHOUSE_ADMIN_PASSWORD="$password"
    OWN_PASSWORD=true
    unset password
  fi
}

step() { echo; echo "== $*"; }

airflow_running() {
  [[ -n "$(docker ps -q --filter 'name=^lakehouse-local-airflow-api-server-1$' 2>/dev/null)" ]]
}

# Recreate Airflow when the product bundles or writers differ from what the last
# start-airflow recorded (extra arguments: --exclude NAME for a removal preview).
apply_airflow() {
  local dry_run="$1" no_restart="$2"
  shift 2
  local current recorded
  current="$(python3 scripts/setup/stage-airflow-writers.py --fingerprint "$@")" || die "the Airflow bundle list could not be generated."
  recorded="$(python3 scripts/setup/airflow-bundle-state.py read)"
  if [[ "$current" == "$recorded" ]]; then
    echo "Airflow bundles and writers are unchanged."
  elif ! airflow_running; then
    echo "Airflow is not running; the next scripts/lakehouse.sh start-airflow registers the new bundles."
  elif [[ "$dry_run" == true ]]; then
    echo "Airflow would be recreated with the bundles: $(python3 scripts/setup/stage-airflow-writers.py --list "$@" | paste -sd ' ' -)"
  elif [[ "$no_restart" == true ]]; then
    echo "Airflow bundles changed; apply them with: scripts/lakehouse.sh start-airflow"
  else
    bash scripts/lakehouse.sh start-airflow
  fi
}

jenkins_running() {
  [[ -n "$(docker ps -q --filter 'name=^lakehouse-local-jenkins-1$' 2>/dev/null)" ]]
}

# Render the Jenkins configuration, folders and jobs, and their state (exit 3 = changed)
# and restart Jenkins when one changed: at start, the init hook applies the folders and
# jobs and deletes the ones that left the product files.
apply_jenkins() {
  local dry_run="$1" no_restart="$2"
  shift 2
  local rc=0
  if [[ "$dry_run" == true ]]; then
    python3 infra/products/render_jenkins.py --check "$@" || rc=$?
    [[ "$rc" == 0 || "$rc" == 3 ]] || die "the Jenkins configuration could not be rendered."
    return 0
  fi
  python3 infra/products/render_jenkins.py "$@" || rc=$?
  [[ "$rc" == 0 || "$rc" == 3 ]] || die "the Jenkins configuration could not be rendered."
  if [[ "$rc" == 3 ]]; then
    if ! jenkins_running; then
      echo "Jenkins is not running; it applies the new configuration at its next start."
    elif [[ "$no_restart" == true ]]; then
      echo "Jenkins configuration changed; restart Jenkins to apply it: docker restart lakehouse-local-jenkins-1"
    else
      docker restart lakehouse-local-jenkins-1 >/dev/null
      echo "Restarted Jenkins to apply the new configuration."
    fi
  fi
}
