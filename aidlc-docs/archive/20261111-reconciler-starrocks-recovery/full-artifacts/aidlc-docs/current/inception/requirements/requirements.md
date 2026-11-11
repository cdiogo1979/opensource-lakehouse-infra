# Requirements — Reconciler and StarRocks Recovery

Recommended options approved in advance by the user.

## Functional Requirements
- **FR-1 Current code**: the scheduled reconciler runs the repository's current `data_products.py`, `reconcile-keycloak-groups.py`, `starrocks_common.py`, `reconcile-starrocks-users.py` and `run.sh`, mounted read-only (the image provides only Python, PyYAML and the MariaDB client), so a product-model change can't leave it stale.
- **FR-2 Bind pattern first**: each cycle first re-applies the StarRocks LDAP bind pattern when the FE lost it (`reconcile-starrocks-users.py --bind-pattern-only`), independently of Keycloak, the product files and the role checks; logins recover within one interval (default 300 s) of an FE restart.
- **FR-3 Visible health**: the reconciler records each fully successful cycle; a container healthcheck reports unhealthy when no cycle succeeded within two intervals plus a margin; `lakehouse.sh status` lists the reconciler's state when it exists.
- **FR-4 Docs**: README and the canonical StarRocks and access designs describe the behavior.

## Non-Functional Requirements
- **NFR-1** No new credential or privilege; the bind-pattern step uses the existing root password file and only sets the existing FE setting.
- **NFR-2** Fail closed: user and group changes still require valid product files and a readable Keycloak.
- **NFR-3** No secret in logs (unchanged handling).

## Security Compliance
SECURITY-03 (logs without secrets), 06 (no new privilege), 11 (secure design), 15 (fail closed): Required. Others N/A (no new data store, endpoint, input surface, dependency or credential).
