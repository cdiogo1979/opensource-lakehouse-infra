#!/usr/bin/env bash
set -euo pipefail
umask 077

SPARK_HOME="${SPARK_HOME:-/opt/spark}"
SPARK_CONTAINER_ROLE="${SPARK_CONTAINER_ROLE:-service}"
RUNTIME_DIR="${SPARK_RUNTIME_DIR:-/run/krb5}"
STATE_FILE="${SPARK_LIFECYCLE_STATE_FILE:-${RUNTIME_DIR}/lifecycle-state}"
WRITER_PRINCIPAL="${SPARK_WRITER_PRINCIPAL:?SPARK_WRITER_PRINCIPAL is required}"
KEYTAB_FILE="${SPARK_WRITER_KEYTAB:?SPARK_WRITER_KEYTAB is required}"
ACCESS_KEY_FILE="${RUSTFS_WRITER_ACCESS_KEY_FILE:-/run/secrets/rustfs-writer-access-key}"
SECRET_KEY_FILE="${RUSTFS_WRITER_SECRET_KEY_FILE:-/run/secrets/rustfs-writer-secret-key}"
KRB5CCNAME="${KRB5CCNAME:-FILE:${RUNTIME_DIR}/ccache}"
AWS_SHARED_CREDENTIALS_FILE="${AWS_SHARED_CREDENTIALS_FILE:-${RUNTIME_DIR}/aws-credentials}"
WRITER_REALM="${WRITER_PRINCIPAL##*@}"

TICKET_RENEW_MARGIN_SECONDS=900
WORKER_DRAIN_GUARD_SECONDS=120
COMMAND_TIMEOUT_SECONDS=30
RETRY_PAUSE_SECONDS=25
LIFECYCLE_POLL_SECONDS=5
WORKER_READY_TIMEOUT_SECONDS=120
WORKER_POLL_SECONDS=2

mkdir -p "${RUNTIME_DIR}" /tmp/spark-events
chmod 700 "${RUNTIME_DIR}"
export KRB5CCNAME AWS_SHARED_CREDENTIALS_FILE
export KRB5_CONFIG="${KRB5_CONFIG:-/etc/krb5.conf}"
export AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_PROFILE=default
export AWS_EC2_METADATA_DISABLED=true
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
unset AWS_WEB_IDENTITY_TOKEN_FILE AWS_ROLE_ARN

SHUTDOWN_REQUESTED=0
NOTEBOOK_PID=""
WORKER_DRAINING=0
DECOMMISSION_REQUESTED=0
NOTEBOOK_STATUS=0
CURRENT_STATE=""

log() {
  printf 'spark-writer: %s\n' "$*"
}

set_state() {
  local new_state="$1"
  [[ "${CURRENT_STATE}" == "${new_state}" ]] && return 0
  local state_tmp="${STATE_FILE}.tmp"
  printf '%s\n' "${new_state}" > "${state_tmp}"
  chmod 600 "${state_tmp}"
  mv -f "${state_tmp}" "${STATE_FILE}"
  CURRENT_STATE="${new_state}"
  log "state=${new_state} principal=${WRITER_PRINCIPAL}"
}

on_signal() {
  SHUTDOWN_REQUESTED=1
}

worker_process_running() {
  "${SPARK_HOME}/sbin/spark-daemon.sh" status org.apache.spark.deploy.worker.Worker 1 >/dev/null 2>&1
}

worker_registered() {
  local master_json
  local master_url="http://127.0.0.1:8080/json/"
  if [[ "${SPARK_CONTAINER_ROLE}" == worker ]]; then
    master_url="http://${SPARK_MASTER_HOST:-spark}:8080/json/"
  fi
  master_json="$(curl --connect-timeout 2 --max-time 3 -fsS "${master_url}" 2>/dev/null)" || return 1
  if [[ "${SPARK_CONTAINER_ROLE}" == worker ]]; then
    local worker_ip worker_host
    worker_ip="$(hostname -i 2>/dev/null | awk '{print $1}')"
    worker_host="$(hostname -s 2>/dev/null)"
    [[ -n "${worker_ip}" ]] || return 1
    [[ "${master_json}" == *"${worker_ip}"* || "${master_json}" == *"${worker_host}"* ]]
  else
    [[ "${master_json}" =~ \"aliveworkers\"[[:space:]]*:[[:space:]]*[1-9] ]]
  fi
}

no_schedulable_workers() {
  local master_json
  master_json="$(curl --connect-timeout 2 --max-time 3 -fsS http://127.0.0.1:8080/json/ 2>/dev/null)" || return 1
  [[ "${master_json}" =~ \"aliveworkers\"[[:space:]]*:[[:space:]]*0([,[:space:]]|$) ]]
}

ticket_expiry_epoch() {
  local expiry
  expiry="$(LC_ALL=C klist -c "${KRB5CCNAME}" 2>/dev/null | awk -v tgt="krbtgt/${WRITER_REALM}@${WRITER_REALM}" 'index($0, tgt) { print $3 " " $4; exit }')" || return 1
  [[ -n "${expiry}" ]] || return 1
  date -d "${expiry}" +%s 2>/dev/null
}

prepare_aws_credentials() {
  local -a access_values=() secret_values=()
  local keytab_mode access_mode secret_mode

  [[ -s "${KEYTAB_FILE}" ]] || { log "required writer keytab is unavailable" >&2; return 1; }
  keytab_mode="$(stat -c '%a' "${KEYTAB_FILE}" 2>/dev/null)" || { log "cannot inspect writer keytab permissions" >&2; return 1; }
  [[ "${keytab_mode}" == 600 ]] || { log "writer keytab must have mode 0600" >&2; return 1; }
  [[ -r "${ACCESS_KEY_FILE}" && -r "${SECRET_KEY_FILE}" ]] || { log "RustFS writer secret files are unavailable" >&2; return 1; }
  access_mode="$(stat -c '%a' "${ACCESS_KEY_FILE}" 2>/dev/null)" || { log "cannot inspect RustFS access-key permissions" >&2; return 1; }
  secret_mode="$(stat -c '%a' "${SECRET_KEY_FILE}" 2>/dev/null)" || { log "cannot inspect RustFS secret-key permissions" >&2; return 1; }
  [[ "${access_mode}" == 600 && "${secret_mode}" == 600 ]] || { log "RustFS writer secret files must have mode 0600" >&2; return 1; }

  mapfile -t access_values < "${ACCESS_KEY_FILE}"
  mapfile -t secret_values < "${SECRET_KEY_FILE}"
  if [[ ${#access_values[@]} -ne 1 || ${#secret_values[@]} -ne 1 || -z "${access_values[0]:-}" || -z "${secret_values[0]:-}" || "${access_values[0]:-}" == *$'\r'* || "${secret_values[0]:-}" == *$'\r'* ]]; then
    log "RustFS writer secret files must each contain one non-empty line" >&2
    return 1
  fi

  {
    printf '[default]\naws_access_key_id=%s\naws_secret_access_key=%s\n' "${access_values[0]}" "${secret_values[0]}"
  } > "${AWS_SHARED_CREDENTIALS_FILE}"
  chmod 600 "${AWS_SHARED_CREDENTIALS_FILE}"
  unset access_values secret_values
}

acquire_ticket() {
  local expiry cache_file
  if ! timeout "${COMMAND_TIMEOUT_SECONDS}s" kinit -c "${KRB5CCNAME}" -kt "${KEYTAB_FILE}" "${WRITER_PRINCIPAL}" >/dev/null 2>&1; then
    return 1
  fi
  case "${KRB5CCNAME}" in
    FILE:*) cache_file="${KRB5CCNAME#FILE:}" ;;
    *) log "Kerberos cache must use a private FILE cache" >&2; return 1 ;;
  esac
  chmod 600 "${cache_file}" 2>/dev/null || return 1
  if ! klist -s -c "${KRB5CCNAME}" >/dev/null 2>&1; then
    return 1
  fi
  expiry="$(ticket_expiry_epoch)" || return 1
  [[ "${expiry}" =~ ^[0-9]+$ ]] || return 1
  TICKET_EXPIRY_EPOCH="${expiry}"
  NEXT_TICKET_ATTEMPT_EPOCH=$((expiry - TICKET_RENEW_MARGIN_SECONDS))
}

start_worker() {
  if worker_process_running; then
    return 0
  fi
  if ! "${SPARK_HOME}/sbin/start-worker.sh" spark://spark:7077 >/dev/null 2>&1; then
    log "Spark worker start command failed"
    return 1
  fi
  log "Spark worker start requested"
}

wait_for_worker() {
  local deadline=$((SECONDS + WORKER_READY_TIMEOUT_SECONDS))
  while (( SECONDS < deadline )); do
    (( SHUTDOWN_REQUESTED == 0 )) || return 1
    worker_registered && return 0
    sleep "${WORKER_POLL_SECONDS}" || true
  done
  return 1
}

shutdown() {
  local status=$?
  trap - EXIT
  set_state STOPPING || true
  if [[ -n "${NOTEBOOK_PID}" ]]; then
    kill -TERM -- "-${NOTEBOOK_PID}" 2>/dev/null || true
  fi
  if [[ "${SPARK_CONTAINER_ROLE}" == service || "${SPARK_CONTAINER_ROLE}" == worker ]]; then
    "${SPARK_HOME}/sbin/stop-worker.sh" >/dev/null 2>&1 || true
  fi
  if [[ "${SPARK_CONTAINER_ROLE}" == service ]]; then
    "${SPARK_HOME}/sbin/stop-history-server.sh" >/dev/null 2>&1 || true
    "${SPARK_HOME}/sbin/stop-master.sh" >/dev/null 2>&1 || true
  fi
  if [[ -n "${NOTEBOOK_PID}" ]]; then
    while kill -0 -- "-${NOTEBOOK_PID}" 2>/dev/null; do
      sleep 1 || true
    done
    wait "${NOTEBOOK_PID}" 2>/dev/null || true
  fi
  kdestroy -c "${KRB5CCNAME}" >/dev/null 2>&1 || true
  rm -f "${AWS_SHARED_CREDENTIALS_FILE}" "${RUNTIME_DIR}/ccache" "${STATE_FILE}.tmp"
  return "${status}"
}

trap shutdown EXIT
trap on_signal HUP INT TERM

case "${SPARK_CONTAINER_ROLE}" in
  service|driver|worker) ;;
  *) log "unsupported SPARK_CONTAINER_ROLE" >&2; exit 2 ;;
esac

set_state STARTING
if ! prepare_aws_credentials; then
  exit 1
fi

TICKET_EXPIRY_EPOCH=0
NEXT_TICKET_ATTEMPT_EPOCH=0
until (( SHUTDOWN_REQUESTED != 0 )); do
  if acquire_ticket; then
    break
  fi
  log "writer TGT unavailable; retrying within 60 seconds"
  sleep "${RETRY_PAUSE_SECONDS}" || true
done
(( SHUTDOWN_REQUESTED == 0 )) || exit 0

if [[ "${SPARK_CONTAINER_ROLE}" == driver || "${SPARK_CONTAINER_ROLE}" == worker ]]; then
  if [[ "${SPARK_CONTAINER_ROLE}" == worker ]]; then
    if ! start_worker || ! wait_for_worker; then
      log "run worker failed to register with the Spark master"
      exit 1
    fi
  else
    if ! curl --connect-timeout 2 --max-time 3 -fsS "http://${SPARK_MASTER_HOST:-spark}:8080/json/" >/dev/null 2>&1; then
      log "Spark master is unavailable to the run driver"
      exit 1
    fi
  fi

  set_state READY
  log "ephemeral role=${SPARK_CONTAINER_ROLE} principal=${WRITER_PRINCIPAL}"
  while (( SHUTDOWN_REQUESTED == 0 )); do
    if [[ "${SPARK_CONTAINER_ROLE}" == worker ]] && ! worker_process_running; then
      log "run worker process exited"
      set_state UNAVAILABLE
      exit 1
    fi
    now="$(date +%s)"
    if ! klist -s -c "${KRB5CCNAME}" >/dev/null 2>&1; then
      log "writer TGT is unavailable"
      set_state UNAVAILABLE
      exit 1
    fi
    TICKET_EXPIRY_EPOCH="$(ticket_expiry_epoch || printf '0')"
    remaining=$((TICKET_EXPIRY_EPOCH - now))
    if (( remaining <= TICKET_RENEW_MARGIN_SECONDS )); then
      if acquire_ticket; then
        log "writer TGT refreshed from keytab"
      else
        log "writer TGT refresh failed"
        set_state UNAVAILABLE
        exit 1
      fi
    fi
    sleep "${LIFECYCLE_POLL_SECONDS}" || true
  done
  exit 0
fi

if ! SPARK_MASTER_HOST=spark "${SPARK_HOME}/sbin/start-master.sh" -p 7077 >/dev/null 2>&1; then
  log "Spark master start command failed"
  exit 1
fi
if ! start_worker; then
  exit 1
fi
if ! "${SPARK_HOME}/sbin/start-history-server.sh" >/dev/null 2>&1; then
  log "Spark history server start command failed"
  exit 1
fi

if ! wait_for_worker; then
  (( SHUTDOWN_REQUESTED != 0 )) && exit 0
  log "Spark worker did not register before the readiness timeout"
  exit 1
fi

if (( $# == 0 )); then
  set -- notebook
fi
setsid "$@" &
NOTEBOOK_PID=$!
set_state READY
log "Spark master endpoint=spark://spark:7077"

while (( SHUTDOWN_REQUESTED == 0 )); do
  if ! kill -0 "${NOTEBOOK_PID}" 2>/dev/null; then
    kill -TERM -- "-${NOTEBOOK_PID}" 2>/dev/null || true
    while kill -0 -- "-${NOTEBOOK_PID}" 2>/dev/null; do
      sleep 1 || true
    done
    if wait "${NOTEBOOK_PID}"; then
      NOTEBOOK_STATUS=0
    else
      NOTEBOOK_STATUS=$?
    fi
    NOTEBOOK_PID=""
    log "notebook child exited"
    exit "${NOTEBOOK_STATUS}"
  fi

  if ! curl --connect-timeout 2 --max-time 3 -fsS http://127.0.0.1:8080/json/ >/dev/null 2>&1; then
    log "Spark master is unavailable"
    exit 1
  fi

  now="$(date +%s)"
  if klist -s -c "${KRB5CCNAME}" >/dev/null 2>&1; then
    TICKET_EXPIRY_EPOCH="$(ticket_expiry_epoch || printf '0')"
  else
    TICKET_EXPIRY_EPOCH=0
  fi
  remaining=$((TICKET_EXPIRY_EPOCH - now))

  if (( remaining <= TICKET_RENEW_MARGIN_SECONDS && now >= NEXT_TICKET_ATTEMPT_EPOCH )); then
    if acquire_ticket; then
      log "writer TGT acquired from keytab"
      now="$(date +%s)"
      remaining=$((TICKET_EXPIRY_EPOCH - now))
    else
      now="$(date +%s)"
      NEXT_TICKET_ATTEMPT_EPOCH=$((now + RETRY_PAUSE_SECONDS))
      log "writer TGT acquisition failed; retrying within 60 seconds"
    fi
  fi

  if (( TICKET_EXPIRY_EPOCH > 0 && remaining > WORKER_DRAIN_GUARD_SECONDS )); then
    if (( WORKER_DRAINING == 0 )); then
      if worker_registered; then
        set_state READY
      else
        set_state RECOVERING
        if ! start_worker; then
          sleep "${RETRY_PAUSE_SECONDS}" || true
          continue
        fi
        if wait_for_worker; then
          set_state READY
        else
          (( SHUTDOWN_REQUESTED != 0 )) && break
          log "Spark worker registration is still pending"
        fi
      fi
    elif ! klist -s -c "${KRB5CCNAME}" >/dev/null 2>&1; then
      set_state UNAVAILABLE
    elif ! worker_process_running; then
      set_state RECOVERING
      if start_worker && wait_for_worker; then
        WORKER_DRAINING=0
        DECOMMISSION_REQUESTED=0
        set_state READY
      else
        (( SHUTDOWN_REQUESTED != 0 )) && break
        set_state UNAVAILABLE
      fi
    fi
  elif (( remaining <= WORKER_DRAIN_GUARD_SECONDS || TICKET_EXPIRY_EPOCH == 0 )); then
    if (( WORKER_DRAINING == 0 )); then
      WORKER_DRAINING=1
      set_state DRAINING
    fi
    if (( DECOMMISSION_REQUESTED == 0 )) || ! no_schedulable_workers; then
      if timeout "${COMMAND_TIMEOUT_SECONDS}s" "${SPARK_HOME}/sbin/decommission-worker.sh" >/dev/null 2>&1; then
        DECOMMISSION_REQUESTED=1
        log "Spark worker graceful decommission requested"
      else
        log "Spark worker decommission request failed; retrying within 60 seconds"
      fi
    fi
    if no_schedulable_workers && ! worker_process_running; then
      DECOMMISSION_REQUESTED=1
      set_state UNAVAILABLE
    fi
  fi

  sleep "${LIFECYCLE_POLL_SECONDS}" || true
done

exit 0
