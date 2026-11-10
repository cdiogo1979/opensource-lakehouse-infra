# Deploy Instructions — Airflow Keycloak SSO

## Scope and status

These are local operator instructions for the Compose-based lakehouse environment. They do not describe or authorize production deployment. The local Airflow stack and Keycloak Airflow client have already been started/configured for testing. Do not repeat the startup command unless a rebuild or restart is needed.

Successful post-fix interactive login remains unverified. Complete that check before treating SSO as operational or promoting the change to another environment.

## Ordered steps

### 1. Confirm prerequisites and authorization

- **Action and target:** Confirm the intended local checkout and Docker Compose environment.
- **Prerequisites:** Review and approve the Deploy handoff separately. Docker Engine/Desktop and Docker Compose V2 must be available. The sibling `opensource-lakehouse` checkout must be present for the configured production/UAT Git Bundles.
- **Execution:** From the infrastructure workspace, inspect `scripts/lakehouse.sh`, `docker-compose.airflow.yml`, and the protected `.runtime/credentials/` directory. Do not display or copy secret values. Confirm that `AIRFLOW_HOST_PORT` is available (default `8085`) and that Keycloak is served at `http://keycloak.localhost:8080`.
- **Validation:** Required credentials are protected files; the Airflow client secret is present and not exposed in logs or source.
- **Failure handling:** Stop if Docker, the sibling checkout, required protected credentials, or the expected loopback ports are unavailable. Resolve the prerequisite rather than bypassing secret checks.

### 2. Apply the local Airflow and Keycloak configuration

- **Action and target:** Start or rebuild the Airflow Compose services and reconcile the Airflow client in the `lakehouse` Keycloak realm.
- **Prerequisites:** Step 1 is complete. A Keycloak administrator credential is available only through the protected local credential file. This command makes additive persistent changes to the local realm.
- **Execution:** From the infrastructure workspace, run:

  ```bash
  scripts/lakehouse.sh start-airflow
  ```

  The script provisions missing local Airflow secrets, prepares certificates and runtime paths, bootstraps the Airflow client and group mapper, builds the images, starts dependencies and Airflow, waits for health, and verifies the production/UAT DAG registrations. It does not run DAGs.
- **Validation:** The command exits successfully. Check service state with:

  ```bash
  scripts/lakehouse.sh airflow-status
  ```

  The API server and token broker should be `healthy`; scheduler, DAG processor, and triggerer should be `running`; dependent services should be `healthy`.
- **Failure handling:** Stop on a bootstrap conflict or readiness failure and inspect sanitized service logs. Do not remove Compose volumes or use `--remove-orphans` as a workaround. Keep the existing Airflow metadata and Keycloak realm state intact while diagnosing.

### 3. Verify endpoints and browser SSO

- **Action and target:** Verify Airflow UI and the Keycloak OIDC callback flow.
- **Prerequisites:** Step 2 completed. Use a Keycloak account assigned to an approved group.
- **Execution:**
  1. Open `http://localhost:8085` (or `http://127.0.0.1:8085`) and choose **Continue with Keycloak**.
  2. Sign in as `joe-developer`, currently expected to belong to `role-default-developer`.
  3. Confirm the browser returns to Airflow and Joe is authenticated with the mapped `Admin` role.
  4. If practical, check a user with no approved group is denied, and verify the separate local administrator recovery route.
  5. Confirm the API version endpoint responds:

     ```bash
     curl -fsS http://localhost:8085/api/v2/version
     ```

- **Validation:** Successful login completes the OAuth callback and reaches the Airflow UI. Joe receives the role associated with `role-default-developer`. A user with no approved group is not provisioned through OAuth.
- **Failure handling:** If the login returns to the login page or reports an error, stop user acceptance and inspect Airflow API-server and Keycloak logs without sharing authorization codes, tokens, cookies, or credentials. Do not weaken group checks or broaden redirect URIs to work around an error. The post-JWKS-fix login has not yet been observed.

### 4. Rollback and recovery

- **Action and target:** Stop the local Airflow services if validation fails or the operator requests shutdown.
- **Prerequisites:** Confirm no operator is relying on the local Airflow instance.
- **Execution:** Run `scripts/lakehouse.sh stop-airflow`. This stops Airflow services and Spark runs while preserving provider data, the Airflow metadata volume, and Bundle checkouts.
- **Validation:** Run `scripts/lakehouse.sh airflow-status` and confirm Airflow services are stopped.
- **Failure handling and limits:** This stop operation does not remove the Airflow OIDC client or mapper from Keycloak and does not undo source changes. No automated Keycloak rollback is provided. If realm rollback is required, a Keycloak administrator must review and perform a separately approved, targeted change; do not delete the realm or modify the unrelated JupyterHub client.

## Environment and approval blockers

- The only tested target is the local Compose environment; no production/staging target, owner, permissions, maintenance window, or external deployment pipeline has been defined.
- Successful browser authentication and role assignment need confirmation after the latest JWKS configuration change.
- Approval of this handoff is not approval to deploy, open a PR, modify another environment, or make further persistent Keycloak changes.
