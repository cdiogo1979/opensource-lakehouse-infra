# Code Generation Plan — reconciler-recovery

- [x] Step 1 — `reconcile-starrocks-users.py`: `--bind-pattern-only` (root login, `ensure_ldap_login`, print the outcome; no Keycloak or product validation).
- [x] Step 2 — `infra/polaris/reconciler/run.sh`: bind-pattern step first each cycle (when StarRocks is enabled); write `/tmp/reconcile-last-success` after a cycle whose group and user syncs both succeeded.
- [x] Step 3 — `compose.core.yml`: mount the five code files read-only over the image copies; healthcheck on the success file's age (2 × interval + 60 s).
- [x] Step 4 — `scripts/lakehouse.sh status`: print the reconciler's state when its container exists.
- [x] Step 5 — Tests (contracts and a property for the healthcheck age rule) and README.
- [x] Step 6 — Local checks.
