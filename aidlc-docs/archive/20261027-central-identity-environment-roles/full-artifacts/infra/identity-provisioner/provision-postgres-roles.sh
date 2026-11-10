#!/bin/bash
set -euo pipefail
umask 077

HIVE_PASSWORD_FILE="/run/secrets/metastore-db-password"
ADMIN_PASSWORD_FILE="/run/secrets/postgres-admin-password"
TEMP_DIR="$(mktemp -d /tmp/postgres-identity.XXXXXX)"
trap 'rm -rf "${TEMP_DIR}"' EXIT

for secret_file in "${HIVE_PASSWORD_FILE}" "${ADMIN_PASSWORD_FILE}"; do
  if [[ ! -s "${secret_file}" || ! -r "${secret_file}" ]]; then
    echo "ERROR: Required PostgreSQL credential file is missing or unreadable."
    exit 1
  fi
done

HIVE_PASSWORD="$(cat "${HIVE_PASSWORD_FILE}")"
ADMIN_PASSWORD="$(cat "${ADMIN_PASSWORD_FILE}")"
if [[ ! "${HIVE_PASSWORD}" =~ ^[a-f0-9]+$ || ! "${ADMIN_PASSWORD}" =~ ^[a-f0-9]+$ ]]; then
  echo "ERROR: PostgreSQL bootstrap passwords must use the generated hexadecimal format."
  exit 1
fi

printf 'metastore-db:5432:metastore:hive:%s\nmetastore-db:5432:metastore:admin:%s\n' \
  "${HIVE_PASSWORD}" "${ADMIN_PASSWORD}" > "${TEMP_DIR}/pgpass"
chmod 600 "${TEMP_DIR}/pgpass"
export PGPASSFILE="${TEMP_DIR}/pgpass"
export PGHOST="metastore-db" PGPORT="5432" PGDATABASE="metastore" PGUSER="hive"

HIVE_ROLE="$(psql -X -qAt -c "SELECT CASE WHEN rolcanlogin THEN CASE WHEN rolsuper THEN 'superuser' ELSE 'restricted' END ELSE 'no-login' END FROM pg_roles WHERE rolname='hive'" 2>/dev/null || true)"
if [[ "${HIVE_ROLE}" == "no-login" || -z "${HIVE_ROLE}" ]]; then
  echo "ERROR: PostgreSQL Hive service role is unavailable; no role changes were made."
  exit 1
fi
HIVE_OID="$(psql -X -qAt -c "SELECT oid FROM pg_roles WHERE rolname='hive'" 2>/dev/null || true)"

ADMIN_ROLE="$(psql -X -qAt -c "SELECT CASE WHEN rolsuper AND rolcanlogin THEN 'ready' ELSE 'invalid' END FROM pg_roles WHERE rolname='admin'" 2>/dev/null || true)"
if [[ "${ADMIN_ROLE}" == "invalid" ]]; then
  echo "ERROR: Existing PostgreSQL admin role lacks the approved superuser/login contract; no password or role was changed."
  exit 1
fi

if [[ "${HIVE_ROLE}" == "restricted" && -z "${ADMIN_ROLE}" ]]; then
  echo "ERROR: Hive is already restricted but PostgreSQL admin is absent; no role changes were made."
  exit 1
fi

ADMIN_PASSWORD_SQL="${ADMIN_PASSWORD//\'/\'\'}"
if [[ -z "${ADMIN_ROLE}" ]]; then
  cat > "${TEMP_DIR}/migration.sql" <<SQL
CREATE ROLE admin WITH LOGIN SUPERUSER PASSWORD '${ADMIN_PASSWORD_SQL}';
SQL
  chmod 600 "${TEMP_DIR}/migration.sql"
  if ! psql -X -q -v ON_ERROR_STOP=1 -f "${TEMP_DIR}/migration.sql" >/dev/null 2>&1; then
    echo "ERROR: PostgreSQL admin role creation failed; inspect database state before retrying."
    exit 1
  fi
  echo "PostgreSQL admin: created"
else
  echo "PostgreSQL admin: already-present"
fi

# PostgreSQL 16 prevents removing SUPERUSER from the bootstrap role (OID 10).
# Convert that role into a no-login bootstrap identity, keep the named admin
# superuser, and create a restricted Hive service role with the same password.
if [[ "${HIVE_ROLE}" == "superuser" && "${HIVE_OID}" == "10" ]]; then
  cat > "${TEMP_DIR}/bootstrap-migration.sql" <<SQL
BEGIN;
ALTER ROLE hive RENAME TO postgres_bootstrap;
ALTER ROLE postgres_bootstrap NOLOGIN;
CREATE ROLE hive WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '${HIVE_PASSWORD}';
GRANT CONNECT ON DATABASE metastore TO hive;
ALTER DATABASE metastore OWNER TO admin;
ALTER SCHEMA public OWNER TO hive;
DO \$migration\$
DECLARE
  obj record;
BEGIN
  FOR obj IN
    SELECT c.relname, c.relkind
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relowner = (SELECT oid FROM pg_roles WHERE rolname = 'postgres_bootstrap')
      AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
    ORDER BY CASE WHEN c.relkind = 'S' THEN 1 ELSE 0 END, c.relkind, c.relname
  LOOP
    IF obj.relkind = 'S' THEN
      EXECUTE format('ALTER SEQUENCE public.%I OWNER TO hive', obj.relname);
    ELSIF obj.relkind = 'v' THEN
      EXECUTE format('ALTER VIEW public.%I OWNER TO hive', obj.relname);
    ELSIF obj.relkind = 'm' THEN
      EXECUTE format('ALTER MATERIALIZED VIEW public.%I OWNER TO hive', obj.relname);
    ELSE
      EXECUTE format('ALTER TABLE public.%I OWNER TO hive', obj.relname);
    END IF;
  END LOOP;
END
\$migration\$;
GRANT USAGE, CREATE ON SCHEMA public TO hive;
COMMIT;
SQL
  chmod 600 "${TEMP_DIR}/bootstrap-migration.sql"
  if ! PGUSER=admin psql -X -q -v ON_ERROR_STOP=1 -f "${TEMP_DIR}/bootstrap-migration.sql" >/dev/null 2>&1; then
    echo "ERROR: PostgreSQL bootstrap-role migration failed; inspect database state before retrying."
    exit 1
  fi
  echo "PostgreSQL bootstrap role: retained as no-login; named admin remains superuser"
  echo "PostgreSQL hive service role: created without superuser privileges; metastore ownership transferred"
elif [[ "${HIVE_ROLE}" == "superuser" ]]; then
  if ! PGUSER=admin psql -X -q -v ON_ERROR_STOP=1 -c "ALTER ROLE hive NOSUPERUSER" >/dev/null 2>&1; then
    echo "ERROR: PostgreSQL Hive role restriction failed; inspect database state before retrying."
    exit 1
  fi
  echo "PostgreSQL hive service role: demoted from superuser"
else
  echo "PostgreSQL hive service role: already-restricted"
fi

ADMIN_STATUS="$(PGUSER=admin psql -X -qAt -c "SELECT CASE WHEN rolsuper AND rolcanlogin THEN 'ready' ELSE 'invalid' END FROM pg_roles WHERE rolname='admin'" 2>/dev/null || true)"
if [[ "${ADMIN_STATUS}" != "ready" ]]; then
  echo "ERROR: PostgreSQL admin authentication or role verification failed."
  exit 1
fi
