# Integration Test Instructions — Polaris Database Path Layout

## Scope

Verify the Polaris catalog/storage mapping, exact Spark table locations, existing environment role matrix, and non-destructive routine bootstrap reruns.

## One-time Local Reset and Recreation

The user explicitly authorized this one-time operation for this local environment. It removes every object/version from the three approved buckets and deletes namespaces, table metadata, and catalog metadata only within the known old/new default-product Polaris catalogs. It preserves buckets and Docker volumes. Do not use this reset as a routine test step.

Polaris currently requires catalog child roles to be removed before deleting the catalogs. The reset script preserves built-in `catalog_admin`; removal of the custom `role-default-*` catalog-role assignments and definitions is pending explicit user approval.

```sh
./scripts/lakehouse.sh start
python3 infra/keycloak/bootstrap-realm.py
./scripts/bootstrap-polaris-realm.sh
python3 infra/rustfs/bootstrap-buckets.py
.runtime/aidlc-test-venv/bin/python infra/polaris/reset-default-product-once.py --confirm-reset-default-product
scripts/bootstrap-default-product.sh
```

Expected table paths:

- `s3://bucket-default/lakehouse/default_lh/bootstrap_smoke_test/`
- `s3://bucket-default-uat/lakehouse_uat/default_lhuat/bootstrap_smoke_test/`
- `s3://bucket-default-dev/lakehouse_dev/default_lhdev/bootstrap_smoke_test/`

## Role Matrix

Run the temporary-identity positive/negative access check. The script creates test clients and probe rows, then attempts cleanup:

```sh
python3 scripts/verify-role-matrix.py
```

Expected behavior is unchanged: developer reads all environments and writes dev; analyst reads production and writes nowhere; owner and writer read/write all three environments.

## Non-destructive Rerun

Create a unique temporary sentinel object in `bucket-default-dev` with the reset venv's boto3 client, rerun `scripts/bootstrap-default-product.sh`, verify the sentinel still exists and the smoke tables still contain only their expected row, then delete only that sentinel. Never run the reset command for this check.

## Limits

This is a local end-to-end validation; it does not certify multi-node or production deployment behavior.
