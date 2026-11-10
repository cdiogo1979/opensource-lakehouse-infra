# Integration Test Instructions — Unit 1 Foundation

## Scope and prerequisites

These checks cover the Unit 1 local foundation: Compose configuration, credentials, KDC service identity, PostgreSQL schema, Hive Metastore readiness, RustFS bucket initialization, and local port exposure. Run from the workspace root with Docker Compose v2. `scripts/start.sh` generates local runtime inputs and waits for the foundation services.

The tests do not claim end-user authorization or impersonation. Unit 2/3 must provision component users and writer ETL; Dremio Hive source/effective-user behavior remains in Unit 4.

## Scenario 1: Compose parse and image build

```bash
./scripts/bootstrap-local.sh
docker compose config --quiet
docker compose build kdc create-bucket hive-schema-init hive-metastore
docker compose pull --ignore-buildable
```

**Expected:** all commands return zero; all Compose service definitions and pinned references parse; custom images build.

## Scenario 2: Ordered startup and readiness

```bash
./scripts/start.sh
docker compose ps --all
```

**Expected:** `kdc`, `metastore-db`, `hive-metastore`, `object-store`, `spark`, and `dremio` are running/healthy; `hive-schema-init` and `create-bucket` exit successfully. PostgreSQL, KDC, Hive Thrift and kadmind have no host-published ports.

Inspect failures without printing environment values:

```bash
docker compose logs --no-color kdc metastore-db hive-schema-init hive-metastore object-store create-bucket
```

## Scenario 3: Kerberos service identity

```bash
docker compose exec kdc /usr/local/sbin/kdc-healthcheck
docker compose exec hive-metastore bash -ec 'echo > /dev/tcp/127.0.0.1/9083'
```

**Expected:** the Hive service keytab obtains a ticket for the configured KDC principal and the Metastore accepts TCP connections on port 9083. This verifies service availability only; it does not verify a Spark/Dremio caller identity or impersonation.

## Scenario 4: Metastore schema and bucket ensure

```bash
docker compose exec hive-schema-init /bin/bash /infra/hive/schema-init.sh
docker compose run --rm create-bucket
```

**Expected:** schema inspection succeeds without changing an already initialized schema; the `lake` bucket is reported as present or created. A rerun must preserve existing objects.

## Scenario 5: Local exposure and credential boundary

```bash
docker compose port dremio 9047
docker compose port object-store 9000
docker compose port spark 8080
find .runtime -maxdepth 4 -type f -exec stat -f '%Sp %N' {} \;
```

**Expected:** published developer ports use `127.0.0.1`; PostgreSQL/Hive/KDC are internal. Credential files remain under ignored `.runtime`; the credentials directory is owner-only. Do not print file contents.

## Deferred integration scenarios

- Spark creates/reads Iceberg tables through Hive as `write-service-account` after Unit 2/3 provisions that identity and its RustFS access.
- Dremio connects to Hive using Kerberos and propagates mapped users after Unit 4 configuration.
- `user_a`/`user_b` per-database allow/deny results after authorization design and identity provisioning.
- Dremio JDBC Space object creation by `write-service-account` after Unit 3/4 feasibility checks.

These remain blocked/deferred and must not be recorded as passing based on service health.

## Cleanup

Stop while preserving data:

```bash
./scripts/stop.sh
```

Use `scripts/clean.sh` only when a destructive reset of all Compose volumes is intended.
