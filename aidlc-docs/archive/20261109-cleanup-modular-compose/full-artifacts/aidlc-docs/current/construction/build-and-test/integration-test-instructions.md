# Integration Tests — Cleanup and Modular Compose

1. **Baseline**: record the container IDs, then run `./scripts/bootstrap-default-product.sh`. Expect exit 0, including the Spark smoke tables in three environments and the StarRocks steps.
2. **No recreation**: run `./scripts/lakehouse.sh start` twice. Container IDs must not change on the second run.
3. **Opt-outs**:
   - Run `JUPYTER_ENABLED=false JENKINS_ENABLED=false STARROCKS_ENABLED=false ./scripts/lakehouse.sh status`, and expect core only.
   - Run the same flags with `start`. Expect one notice per disabled module, unchanged module containers, and no orphan warnings.
4. **Stop and start**: run `./scripts/lakehouse.sh stop`. Status shows everything stopped. Then `start`: everything is healthy with the same container IDs.
5. **Verifiers**:
   - `scripts/verify/{rustfs-oidc,rustfs-sts,polaris-oidc-negative-cases,polaris-keycloak-auth,role-matrix,jenkins-oidc}.py`
   - `scripts/verify/airflow-dags.sh` with the Airflow environment from `lakehouse.sh`
   - `scripts/clients/starrocks-login.sh`
