# Integration and End-to-End Tests — StarRocks Integration

Run against the live stack after the build steps. Probe objects use the prefix `sr_bt_` and are removed afterwards.

1. **Runtime**: FE and BE are healthy. `SHOW BACKENDS` shows `starrocks-be` alive. Rerunning `bootstrap-starrocks.py --runtime-only` reports `already-set` and `already-registered`.
2. **Catalogs**: a full bootstrap creates the three catalogs, then reports `equal`. Root reads the three smoke tables through Polaris-vended credentials.
3. **JWT login**: `scripts/starrocks-login.sh --password-file <file> <user> -e "SELECT CURRENT_USER(), CURRENT_ROLE()"` for each bootstrap user. Expect verified TLS and the user's role.
4. **Access matrix**: per user, read each environment's smoke table, then `CREATE TABLE` and `INSERT` a probe table in each environment and attempt `DROP TABLE` in dev. Compare with the role matrix (README "Roles").
5. **MVs**:
   - The writer creates an async MV in `default_lhdev` over the dev smoke table and refreshes it synchronously.
   - Developer reads it. Analyst is denied. Developer refresh is denied.
   - `information_schema.task_runs` shows scheduled refreshes. The writer drops the MV.
6. **Reconcile**: add a group to a user, create a temporary product-group user, reconcile, then reverse both and reconcile. Expect grant, create, revoke, and drop, and finally zero changes.
7. **Enforcement**: as root, add an extra privilege to a managed role. The bootstrap revokes it and reports it.
8. **Opt-out**: `STARROCKS_ENABLED=false` makes both scripts print a notice and leaves StarRocks out of `lakehouse.sh status`.
9. **Scheduled**: the `polaris-group-reconciler` log shows a successful StarRocks reconcile.
10. **Regression**: `verify-rustfs-oidc`, `verify-rustfs-sts`, `verify-polaris-oidc-negative-cases`, `verify-polaris-keycloak-auth`, `verify-role-matrix` (identity and Polaris parts), and `verify-jenkins-oidc`.
11. **Cleanup**: drop the probe tables through the Polaris REST API as an owner, without purge (Polaris refuses purge).
