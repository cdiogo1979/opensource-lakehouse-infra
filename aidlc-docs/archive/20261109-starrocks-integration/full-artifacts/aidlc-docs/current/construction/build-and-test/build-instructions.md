# Build Instructions — StarRocks Integration

## Prerequisites
- Docker with Compose V2 (tested on Rancher Desktop with 6 CPUs and about 16 GB, `linux/arm64`), Python 3, and OpenSSL.
- Images (pulled, no build): `starrocks/fe-ubuntu:4.1.7` and `be-ubuntu:4.1.7` (digests in `docker-compose.starrocks.yml`), and `mysql:9.7.2` for logins. The `polaris-group-reconciler` image is rebuilt with `mariadb-client`.
- `.env`: `STARROCKS_ENABLED` defaults to true.

## Code analysis
No linter is configured. The static checks run were:
- `bash -n` on all scripts and `infra/starrocks/fe-entrypoint.sh`
- `sh -n` on the reconciler `run.sh`
- `python3 -m py_compile` on the changed Python files
- `docker compose ... config -q` for the core and StarRocks files, and for the core, StarRocks, and Airflow files

## Build and start
```sh
./scripts/lakehouse.sh start            # adds certificates, FE and BE, root password, and BE registration
./scripts/bootstrap-default-product.sh  # adds the StarRocks catalogs, MV databases, roles, and users
```

## Expected output
- `StarRocks root password: set` on the first run, then `already-set`.
- `StarRocks backend: registered`, then `already-registered`.
- `StarRocks catalog <name>: create`, then `equal`.
- `StarRocks roles: 5 managed; N grant(s) applied, 0 revoked`. A rerun re-issues about 30 idempotent `ALL` grants, because StarRocks reports `ALL` as individual privileges.
- `StarRocks read <catalog>.<ns>.bootstrap_smoke_test: 1 row(s).` for all three catalogs.
- `StarRocks users reconciled: 5 desired; ...`
