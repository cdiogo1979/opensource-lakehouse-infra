# Code Structure — Reset and Identity Bootstrap

## Files likely to change
- `scripts/lakehouse.sh`: entry points (`start`, `stop`, `status`, `start-airflow`, `remove-legacy-jenkins`); a new `reset` command is the natural home.
- `infra/keycloak/bootstrap-realm.py`: groups, `platform-admin` creation (`ensure_owner_user`), and memberships. The bootstrap users would be added here.
- `infra/keycloak/realm-contract.json`: the declared groups and clients.
- `scripts/prepare-lakehouse-runtime.py`: creates credentials once, including `platform-admin-password`.
- `scripts/bootstrap-default-product.sh`: the end-to-end bootstrap; it runs Polaris group reconciliation, which creates principals for group members.
- `infra/polaris/reconcile-keycloak-groups.py`, `infra/airflow/airflow_sso_roles.py`, `infra/jenkins/casc/jenkins.yaml`, `infra/rustfs/bootstrap-policies.py`, `infra/jupyter/hub/lakehouse_policy.py`: the group consumers, to change only if `role-platform-admin` must grant rights.
- `README.md`: start, reset, and user documentation.
- `infra/polaris/reset-default-product-once.py`: the existing narrow reset (keep, replace, or reference).
