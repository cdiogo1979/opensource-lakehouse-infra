# Deploy Handoff — Polaris Database Path Layout

## Handoff status

The approved local implementation and Build and Test are complete. The one-time reset and fresh bootstrap were executed against the local Docker Compose stack. This handoff records the operator sequence and verification evidence; it does not run a deployment, create a pull request, or claim production readiness.

## Current resource layout

| Environment | Polaris catalog | Database namespace | RustFS bucket | Verified table location |
|---|---|---|---|---|
| Production | `lakehouse` | `default_lh` | `bucket-default` | `s3://bucket-default/lakehouse/default_lh/bootstrap_smoke_test/` |
| UAT | `lakehouse_uat` | `default_lhuat` | `bucket-default-uat` | `s3://bucket-default-uat/lakehouse_uat/default_lhuat/bootstrap_smoke_test/` |
| Development | `lakehouse_dev` | `default_lhdev` | `bucket-default-dev` | `s3://bucket-default-dev/lakehouse_dev/default_lhdev/bootstrap_smoke_test/` |

The resolved layout is `<bucket>/<catalog>/<database>/<table>`; each segment appears once.

## Verified operator workflow

The current local stack is running. For a later normal start or bootstrap rerun:

```sh
./scripts/lakehouse.sh start
./scripts/lakehouse.sh status
scripts/bootstrap-default-product.sh
```

Normal bootstrap is non-destructive: existing bucket contents are preserved, catalogs/namespaces and grants are reconciled, and Spark verifies smoke-table creation and readback for all three environments. A rerun was tested with an existing dev-bucket sentinel object; the object survived and was removed by the verification check.

To stop services while retaining state:

```sh
./scripts/lakehouse.sh stop
```

Do not use `docker compose down -v` for routine shutdown; it removes named volumes.

## Destructive reset boundary

The one-time reset for this intent has already been executed. It removed 48 object versions from `bucket-default`, 48 from `bucket-default-uat`, and 63 from `bucket-default-dev`, while retaining the bucket resources. It removed only the approved custom default-product catalog roles and their assignments from the known old/new catalog set; Polaris's built-in `catalog_admin` was preserved. Normal bootstrap then recreated the approved catalogs, namespaces, grants, Keycloak group mappings, and smoke tables.

Do not run the reset again unless a complete purge of all objects and versions in those three buckets is explicitly intended. The guarded command is:

```sh
python3 -m pip install -r infra/bucket-init/requirements.txt
./scripts/lakehouse.sh start
python3 infra/keycloak/bootstrap-realm.py
./scripts/bootstrap-polaris-realm.sh
python3 infra/rustfs/bootstrap-buckets.py
python3 infra/polaris/reset-default-product-once.py --confirm-reset-default-product
scripts/bootstrap-default-product.sh
```

Review `infra/polaris/reset-default-product-once.py` target guards before any future use. The reset removes every object version in the three named buckets. It does not delete bucket resources or named volumes. It is not invoked by normal bootstrap.

## Verification evidence

- Python compilation, Bash syntax, and `docker compose config --quiet` passed.
- Local Keycloak, Polaris, RustFS, and both PostgreSQL providers reached healthy status.
- Normal bootstrap passed twice. Keycloak memberships and Polaris catalog grants reconciled; expected writer denial (HTTP 403) and invalid-signature rejection (HTTP 401) were verified.
- Spark created/read back smoke tables and confirmed vended-credential access at each exact table location above.
- `python3 scripts/verify-role-matrix.py` passed for developer, analyst, owner, and writer across prod, dev, and UAT. Temporary identities and probe rows were removed, and each smoke table returned to its original single row.
- A unique pre-existing object in `bucket-default-dev` survived a normal bootstrap rerun; the check then removed only that sentinel.

Full details: [`../construction/build-and-test/build-and-test-summary.md`](../construction/build-and-test/build-and-test-summary.md).

## Rollback and operating limits

- The pre-reset bucket objects are not recoverable from this workflow; no backup was created before the approved purge. Restore them only from an independent backup, if one exists.
- The old catalog metadata was reset and recreated. The reset does not include an automatic rollback or backup.
- To pause the local stack without deleting data, use `./scripts/lakehouse.sh stop`. Retained Docker volumes preserve current Polaris, Keycloak, and RustFS state.
- The verified scope is the local single-host Docker Compose environment. This change does not certify production, high availability, multi-host use, or deferred Airflow/JupyterHub/Jenkins/StarRocks integrations.
- The approved single-realm Polaris configuration uses the current local issuer/JWKS arrangement and relaxed realm-header requirement for Iceberg 1.8.1's vended-credential refresh behavior. Keep this deployment to the configured `lakehouse` realm unless strict realm-header validation is restored with a compatible client.

## Release boundary

No external deployment, commit, push, or pull request was performed as part of this handoff.
