#!/bin/sh
set -eu

umask 077
PGPASSFILE=/run/polaris/pgpass
export PGPASSFILE

until pg_isready -h polaris-db -U polaris -d polaris >/dev/null 2>&1; do
  sleep 2
done

psql --no-psqlrc --set ON_ERROR_STOP=1 \
  --host polaris-db --username polaris --dbname polaris \
  --command 'CREATE SCHEMA IF NOT EXISTS polaris_schema AUTHORIZATION polaris;' \
  >/dev/null
echo 'Polaris metadata schema is ready.'
