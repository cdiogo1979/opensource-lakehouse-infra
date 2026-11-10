# Business Logic Model — environment-reset-bootstrap-users

## Reset (`scripts/lakehouse.sh reset [--yes|--dry-run]` → `scripts/reset-lakehouse.py`)
1. Discover the inventory (RB-9) and print it, grouped by kind.
2. `--dry-run`: stop here. Otherwise ask for `reset`, unless `--yes` is given.
3. Force-remove the selected containers.
4. Remove the volumes.
5. Remove the networks.
6. Delete the three `.runtime` subdirectories.
7. Report the result. A rerun finds nothing and succeeds.

## Startup
1. `scripts/lakehouse.sh start`: unchanged sequence. Runtime preparation now also writes `srv-default-writer-password` from `bootstrap-users.json`. The realm bootstrap creates the groups, the `lakehouse-writer` client, and missing bootstrap users (RB-1).
2. `scripts/bootstrap-default-product.sh`: realm, then `scripts/bootstrap-users.sh` (RB-2), then the Polaris realm, buckets, policies (including `role-platform-admin`), catalogs, authorization, and group reconciliation (including the `role-platform-admin` → `role-default-owner` mapping). Then the writer verification and the Spark smoke job, both as `srv-default-writer`.
3. `scripts/lakehouse.sh start-airflow`: prepares secrets, creates `<repo>/.runtime/airflow-dag-bundles`, validates the Bundle root, and starts Airflow. The broker issues writer tokens through the password grant.

## Bundle move (one-time, in Build and Test)
1. Restart Airflow with the new root, so it re-clones the Bundles.
2. Confirm DAG registration.
3. Remove `../opensource-lakehouse/.runtime`.

## Failure behavior
- **Wrong or missing writer password or client secret**: the broker returns `identity_provider_failure` and Spark fails closed.
- **A user already exists with other groups**: start leaves it alone. The user bootstrap normalizes it.
- **Reset partially fails** (for example, a container is in use): it stops with the remaining items listed; rerun after fixing.
