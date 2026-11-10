# End-to-End Test Instructions — JupyterHub, Spark, Polaris, and RustFS

## Purpose and safety

Verify the full user journeys through browser OIDC, JupyterHub admission, isolated Spark, Polaris authorization, and Polaris-vended RustFS credentials. These are local acceptance checks, not production certification.

- Use temporary developer, analyst, and unapproved test users where available. Keep passwords in a password manager; never put them in shell history, notebooks, test reports, or this repository.
- Use only the existing smoke tables and uniquely named test rows/objects. Save only non-secret outcomes. Remove only resources created for the test.
- Never copy, print, or persist access JWTs, refresh tokens, RustFS temporary credentials, client secrets, or admin passwords.
- Do not reset buckets/catalogs/databases, edit existing role grants, or run `docker compose down -v`.

## Readiness

1. Review container state before starting or reconfiguring anything.
2. Start the local stack using the supported command and wait for every service to report healthy:

   ```bash
   scripts/lakehouse.sh start
   scripts/lakehouse.sh status
   ```

3. Confirm the browser endpoints are loopback-only: JupyterHub at `http://jupyterhub.localhost:8000`, Keycloak at `http://keycloak.localhost:8080`, and Polaris REST at `http://127.0.0.1:8181`.
4. Confirm Polaris management port 8182 remains unpublished and container-loopback-only. Do not expose it to the host or user-server network.

## Browser and server journey

For a temporary user in `role-default-developer`:

1. Open JupyterHub and complete the Keycloak browser Authorization Code + PKCE login.
2. Confirm the user is admitted and receives a Spark-enabled Jupyter server.
3. Stop and restart that user's server. Confirm the named home persists.
4. Confirm the user's container has no Docker socket, has a distinct home volume, and is attached only to `jupyter-user` and `data-access`, not `core`.

Repeat with a temporary `role-default-analyst` user. Then verify an unapproved user, or a user removed from both approved groups, cannot start a new server. Group removal does not stop an already-running server; stop that server explicitly before checking revoked access.

## Spark and data access matrix

Start a user session through the supported notebook API:

```python
from lakehouse_spark import create_spark_session

spark = create_spark_session()
```

Use fresh uncached table operations and record only success/denial, table name, and environment:

| User role | Read production | Read UAT | Read dev | Write production | Write UAT | Write dev |
|---|---:|---:|---:|---:|---:|---:|
| Developer | Allow | Allow | Allow | Deny | Deny | Allow |
| Analyst | Allow | Deny | Deny | Deny | Deny | Deny |

The automated service-account role matrix is available separately in `integration-test-instructions.md`. It verifies table locations and vended-credential query behavior but does not, by itself, prove RustFS STS policy details or direct object-scope denial.

## Token and credential expiry behavior

The approved Keycloak human access JWT lifetime is 300 seconds. Spark OAuth renewal is disabled so an active session cannot silently change user identity. Polaris-vended RustFS credentials now target 3600 seconds with a 600-second cache; verify the actual returned lifetime and session policy against the pinned services.

1. Start a fresh Spark session and note the start time without inspecting or logging its JWT.
2. After the JWT has expired, force a new Polaris metadata/authenticated operation that cannot use cached metadata. Confirm it fails closed and emits no token or credential value.
3. Start a new Spark session. Confirm the broker supplies a fresh user identity and the approved read/write matrix still applies.
4. To inspect the vended RustFS credential refresh path, exercise it only through the pinned Iceberg/Polaris client and record safe status, elapsed time, and expiry metadata if exposed. Never print or serialize credential contents.
5. Do not claim in-session JWT renewal. With the current contract, a request requiring Polaris after JWT expiry is expected to be denied; successful continuation requires a new Spark session.

If the client does not expose a safe way to observe the returned STS duration/session scope or force refresh without logging secrets, record that check as unverified. Do not infer direct S3 scope from a Polaris SQL denial.

## Cleanup and evidence

1. Stop temporary Jupyter servers and remove only temporary users/clients created for the run.
2. Remove only test rows and objects carrying the unique run identifier; verify existing smoke rows and unrelated objects remain unchanged.
3. Confirm temporary credential files and temporary Polaris principals are absent.
4. Review test output and service logs for JWT-shaped strings, refresh tokens, client secrets, passwords, or RustFS keys. Save redacted logs only.
5. Record checks as **passed**, **failed**, or **unverified**. A skipped or inaccessible check is not a pass.

Routine stack stop preserves named volumes and lake data:

```bash
scripts/lakehouse.sh stop
```

Do not remove persistent volumes as part of this test.
