# Focused Reverse Engineering — Reconciler and StarRocks Recovery

## Symptoms (2026-11-11)
- After a StarRocks FE restart at 00:27:49, password logins failed ("empty password is not allowed for simple authentication") for more than five minutes, although the canonical design says the scheduled user sync re-applies the bind pattern within five minutes.

## Findings
- `polaris-group-reconciler` (profile `scheduled-reconciliation`, image `local/lakehouse-polaris-group-reconciler:1.0.0`, built 2026-11-09T20:40) fails **every** cycle: `default.yaml has unknown keys: repo` for both the Keycloak-to-Polaris group sync and the StarRocks user sync. Its image COPYs `data_products.py`, the reconcile scripts and `starrocks_common.py` at build time; the repository's product model gained the `repo` block afterwards (hashes differ). Only `scripts/bootstrap-default-product.sh` rebuilds it (`up -d --build`); `lakehouse.sh start` and the product commands don't.
- The StarRocks user sync applies the bind pattern (`ensure_ldap_login`) only after product validation, the Keycloak read and the managed-role check, so any of those failing also blocks the login recovery.
- Nothing surfaces the failure: the container has no healthcheck and `lakehouse.sh status` doesn't show it.
- The host-run syncs (product bootstrap and commands, `reconcile-starrocks`) use the current code, so Polaris principals and StarRocks users were kept current by them; a StarRocks dry run reported no pending change.
