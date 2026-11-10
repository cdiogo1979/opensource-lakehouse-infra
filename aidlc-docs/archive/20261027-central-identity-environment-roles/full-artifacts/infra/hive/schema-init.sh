#!/bin/bash
set -euo pipefail

SCHEMATOOL="/opt/hive/bin/schematool"
EXPECTED_SCHEMA_VERSION="${HIVE_METASTORE_SCHEMA_VERSION:-3.1.0}"

# The upstream image entrypoint links HIVE_CUSTOM_CONF_DIR into HIVE_CONF_DIR.
# This service overrides that entrypoint to run schematool, so apply the same
# config-directory setup here before invoking the tool.
export HIVE_HOME="${HIVE_HOME:-/opt/hive}"
export HIVE_CONF_DIR="${HIVE_CONF_DIR:-${HIVE_HOME}/conf}"
if [[ -d "${HIVE_CUSTOM_CONF_DIR:-}" ]]; then
  find "${HIVE_CUSTOM_CONF_DIR}" -type f -exec ln -sfn {} "${HIVE_CONF_DIR}"/ \;
  export HADOOP_CONF_DIR="${HIVE_CONF_DIR}"
  export TEZ_CONF_DIR="${HIVE_CONF_DIR}"
fi

if [[ ! -x "${SCHEMATOOL}" ]]; then
  echo "ERROR: Hive 3.1.3 schematool is unavailable at the expected path." >&2
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "ERROR: PostgreSQL client is required to inspect schema state safely." >&2
  exit 1
fi

if [[ ! -r /run/secrets/metastore-db-password ]]; then
  echo "ERROR: PostgreSQL password secret is unavailable to the schema initializer." >&2
  exit 1
fi

psql_query() {
  PGPASSWORD="$(cat /run/secrets/metastore-db-password)" \
    psql -X -A -t -v ON_ERROR_STOP=1 \
      -h "${METASTORE_DB_HOST:-metastore-db}" \
      -U "${METASTORE_DB_USER:-hive}" \
      -d "${METASTORE_DB_NAME:-metastore}" \
      -c "$1"
}

table_count="$(psql_query "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';")"
if [[ ! "${table_count}" =~ ^[0-9]+$ ]]; then
  echo "ERROR: Could not determine whether the PostgreSQL schema is empty; refusing schema initialization." >&2
  exit 1
fi

if [[ "${table_count}" == "0" ]]; then
  echo "PostgreSQL metastore is empty; initializing Hive schema ${EXPECTED_SCHEMA_VERSION}."
  "${SCHEMATOOL}" -dbType postgres -initSchema
else
  if ! schema_version="$(psql_query 'SELECT "SCHEMA_VERSION" FROM public."VERSION";')"; then
    echo "ERROR: PostgreSQL has existing tables but no readable Hive VERSION metadata; refusing schema initialization." >&2
    exit 1
  fi
  if [[ "${schema_version}" != "${EXPECTED_SCHEMA_VERSION}" ]]; then
    echo "ERROR: Existing Hive schema version '${schema_version:-<empty>}' does not match expected '${EXPECTED_SCHEMA_VERSION}'; refusing initialization or upgrade." >&2
    exit 1
  fi
  echo "Hive Metastore schema ${schema_version} already exists; leaving it unchanged."
fi

schema_version="$(psql_query 'SELECT "SCHEMA_VERSION" FROM public."VERSION";')"
if [[ "${schema_version}" != "${EXPECTED_SCHEMA_VERSION}" ]]; then
  echo "ERROR: Hive schema verification returned '${schema_version:-<empty>}' instead of '${EXPECTED_SCHEMA_VERSION}'." >&2
  exit 1
fi
echo "Hive Metastore PostgreSQL schema verified at version ${schema_version}."
