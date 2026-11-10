# Integration Test Instructions — jenkins-keycloak-sso

1. **Read-only wiring**: `python3 scripts/verify-jenkins-oidc.py` reports 9/9. It checks:
   - health, and that anonymous access is denied
   - login redirects and accepted callbacks for both loopback hosts
   - the running plugins equal `plugins.txt`
   - the OIDC realm and matrix, the migrated job, and the home marker
   - that no secrets appear in `docker inspect`
2. **Idempotency**: rerun `bootstrap-realm.py` and `migrate-jenkins-home.py`. Expected: no changes, and `already initialised`.
3. **Restart**: `docker compose restart jenkins`. It becomes healthy again, configuration as code is reapplied, and step 1 passes again.
4. **Headless SSO and permissions** (`e2e-jenkins-oidc.py.txt`): run with `python3 -I <script> <repo-root>`. It creates temporary owner, developer, analyst, writer, and no-group users and drives the real Jenkins → Keycloak → `finishLogin` flow. It checks:
   - authorities and Overall/Read
   - Administer
   - Job/Read
   - build permission: analyst denied, developer allowed
   - the escape-hatch login
   - logout through Keycloak
   - the result of the developer-triggered workload build

   It always deletes the temporary users.
5. **Regression**: `python3 scripts/verify-rustfs-oidc.py` passes; the Airflow UI and JupyterHub stay healthy.
6. **Interactive**: sign in at <http://127.0.0.1:8090> with Keycloak and confirm you see what your group allows.
