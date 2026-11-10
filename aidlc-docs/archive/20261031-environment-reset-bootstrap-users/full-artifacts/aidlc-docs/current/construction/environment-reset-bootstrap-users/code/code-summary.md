# Code Summary — Environment Reset and Bootstrap Users

Intent `20261031-environment-reset-bootstrap-users`. Code generation is complete. Nothing has been run against the live environment yet; that happens in Build and Test.

## Requirements traceability

| Requirement | Change |
|---|---|
| FR-1 Full reset | New `scripts/reset-lakehouse.py`, exposed as `scripts/lakehouse.sh reset [--yes\|--dry-run]`. It finds resources by Compose project label, runtime role label, exact volume and network names, and the `lakehouse-jupyter-home-` prefix. It deletes containers, then volumes, then networks, then `.runtime/{credentials,container-mounts,airflow-dag-bundles}`. A path guard rejects symlinks and anything else. Images and other projects are never touched. |
| FR-2 Confirmation | Without `--yes`, the user must type `reset` in a terminal. A run without a terminal is refused. `--dry-run` only prints the list. The two flags are mutually exclusive. |
| FR-3 Bootstrap users | New `infra/keycloak/bootstrap-users.json` is the single source for the five users, their groups, and `ChangeM3!`. `bootstrap-realm.py` creates missing users only, with a permanent password and no required actions. |
| FR-4 Enforce defaults on rerun | New `infra/keycloak/bootstrap-users.py` and `scripts/bootstrap-users.sh`. For each listed user they create or update the profile, reset the password (non-temporary), remove other groups, and add the default group. Users not in the list are untouched. The script is called from `scripts/bootstrap-default-product.sh` after the realm bootstrap. |
| FR-5 `role-platform-admin` | New Keycloak group with the Polaris client role `role-default-owner`. Polaris reconciler maps it to the owner principal role. RustFS policy equals the owner policy. Airflow maps it to `Admin` and Jenkins to `Overall/Administer`. `realm-contract.json` updated. |
| FR-6 Replace `write-service-account` | New confidential client `lakehouse-writer` (password grant only, 1-hour tokens, Polaris mapper). The Airflow token broker, Spark smoke tables, and three verifiers authenticate as `srv-default-writer`. `prepare-lakehouse-runtime.py` writes `.runtime/credentials/srv-default-writer-password` from the JSON file. The old owner-user logic and `platform-admin-password` were removed. |
| FR-7 Startup | The two-step start is unchanged: `lakehouse.sh start`, then `bootstrap-default-product.sh`. |
| FR-8 README | New sections "Start the platform" (with the users table) and "Reset the platform". Obsolete `platform-admin-password`, `--owner-username`, and `write-service-account` text removed. |
| FR-9 Independent repositories | Airflow Bundles now live in `<infra-v2>/.runtime/airflow-dag-bundles`. `LAKEHOUSE_PROJECT_ROOT` is removed from `lakehouse.sh`, `provision-airflow-secrets.sh`, `validate-bundle-config.py`, and `docker-compose.airflow.yml`. The one-time removal of `../opensource-lakehouse/.runtime` is a Build and Test step. |

## Tests

New files:

- `tests/keycloak/test_bootstrap_users_contract.py` (9 tests)
- `tests/operations/test_reset_lakehouse.py` (6 tests)
- `tests/airflow/test_bundle_root_contract.py` (3 tests)

Updated files: the RustFS policy contract, the Jenkins CasC contract, and the Airflow SSO contract.

Full suite: 183 passed, 1 skipped, 2 failed. The JupyterHub broker test (10 passed) needs `PYTHONPATH=infra/jupyter/hub`. The 2 failures are the earlier Airflow developer-role drift (code `User`, tests `Admin`). They are out of scope and were not changed. Bash syntax, Python compilation, and Compose rendering with the Airflow overlay also passed.

## Pending for Build and Test

- `scripts/run-bootstrap-smoke-spark.sh` still uses the legacy image `local/spark-iceberg:3.5.5_1.8.1-krb5`. Check that it is present and works with the password grant.
- The live cycle, run only with your approval and after the backup reminder:
  1. reset
  2. start
  3. product bootstrap
  4. log in as each user
  5. rerun `bootstrap-users.sh`
  6. run the verifiers
  7. start Airflow and get a broker token as `srv-default-writer`
  8. remove `../opensource-lakehouse/.runtime`

## Build and Test change

`infra/airflow/validate-bundle-config.py` checks the host root only with `--host-paths`, which `scripts/lakehouse.sh` passes. The copy in the image runs without the flag. This fixes an `airflow-init` failure found in Build and Test.
