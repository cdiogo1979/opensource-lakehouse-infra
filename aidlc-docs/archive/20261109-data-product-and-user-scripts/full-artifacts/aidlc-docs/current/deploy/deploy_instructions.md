# Deployment Instructions — Data products and user scripts

**Applies to**: an existing stack running the previous version, on one machine. It is already done on the stack used in Build and Test.

**Manual or automated**: every step is run by hand, in this order.

**Required inputs**:
- the `platform-admin` password (or another member of `role-platform-admin`)
- a maintenance window for the brief Polaris, Jenkins, JupyterHub, and Airflow restarts

## 1. Baseline the default product's access
- **Prerequisites**: the stack is running, and the Spark runtime image `local/lakehouse-spark-runtime:3.5.5_1.10.2` exists.
- **Execution**: `python3 scripts/verify/role-matrix.py > baseline.txt`.
- **Validation**: four `ROLE_MATRIX_RESULT` lines and a `ROLE_MATRIX_CLEANUP` line.
- **Failure handling**: stop. Do not migrate a stack whose baseline fails.

## 2. Merge the Polaris settings and restart Polaris
- **Execution**:
  - `python3 scripts/setup/prepare-runtime.py`, which merges `infra/polaris/oidc.properties` and renders `.runtime/container-mounts/jenkins-casc.yaml`
  - then `docker restart lakehouse-local-polaris-1`
- **Validation**:
  - `docker exec lakehouse-local-polaris-1 grep ALLOW_NAMESPACE_CUSTOM_LOCATION /deployment/config/application.properties` prints the line.
  - The container becomes healthy.
- **Failure handling**: restore the previous `oidc.properties`, rerun `prepare-runtime.py`, and restart Polaris. Data is untouched.

## 3. Recreate the apps and rebuild the sync job
- **Execution**:
  1. `scripts/lakehouse.sh start` (JupyterHub and Jenkins)
  2. `scripts/lakehouse.sh start-airflow` (only if Airflow is used)
  3. `docker compose -f compose.core.yml --profile scheduled-reconciliation up -d --build polaris-group-reconciler`
- **Validation**:
  - Every service is healthy.
  - `docker logs lakehouse-local-polaris-group-reconciler-1` shows both syncs succeeding.
- **Failure handling**: read the failing container's log. The previous images remain available for a rollback of the code.

## 4. Migrate the default product's grants
- **Execution**:
  1. `scripts/operations/create-data-product.sh data-products/default.yaml --dry-run --admin-password-file <file>`
  2. Review the plan.
  3. Run it again without `--dry-run`.
- **Validation**: a second `python3 infra/polaris/bootstrap-product-authorization.py --dry-run` plans `grants-added=0; grants-revoked=0`.
- **Failure handling**: the step is idempotent; rerun it after fixing the cause. Additions run before revocations, so access does not drop mid-way. There is **no automated rollback** to catalog-wide grants: restoring them means reinstating the previous code and rerunning its `bootstrap-product-authorization.py`.

## 5. Verify
- **Execution**: `python3 scripts/verify/role-matrix.py`, then compare with `baseline.txt`.
- **Validation**:
  - The `ROLE_MATRIX_RESULT` lines are identical to the baseline.
  - `python3 scripts/verify/polaris-keycloak-auth.py` passes.
- **Failure handling**: if they differ, stop and investigate before creating new products.

## 6. Optional: create the first new product
Follow the README section "Data products":
1. `create-data-product.sh --init <name>`
2. Review the file.
3. Apply it.
4. Check it with `role-matrix.py --product <name>`.
