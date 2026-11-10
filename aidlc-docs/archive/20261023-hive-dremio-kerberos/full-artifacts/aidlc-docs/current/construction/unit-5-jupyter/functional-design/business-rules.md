# Unit 5 JupyterHub and Per-User Spark — Business Rules

## User and Session Mapping

1. The only configured development usernames are `user_a`, `user_b`, and `admin`; all other usernames are rejected before credentials are mounted.
2. DummyAuthenticator accepts username labels without verifying a person's identity. The Hub is for isolated local PoC use and must not be exposed as an authenticated service.
3. A username maps only to the same-named provisioned Kerberos principal and RustFS account. No session may use `admin`, `write-service-account`, RustFS root, or another user's credentials as a fallback.
4. `admin` has the JupyterHub administrator role and a separate `admin` Spark identity. Hub administration does not imply that the admin Spark query passes the `user_a`/`user_b` access acceptance matrix.
5. Each username receives a distinct single-user container and a separate persistent work volume. No shared directory is writable by multiple users.

## Kerberos, Hive, and RustFS

6. Each session mounts only its matching keytab read-only and uses a private ticket cache scoped to that container/session.
7. A session obtains its ticket as the matching principal before opening the Spark/Hive path; failure to authenticate prevents query execution.
8. A session receives only its matching RustFS credential. RustFS credentials are separate from Kerberos credentials, and direct RustFS access is not a test acceptance case.
9. Jupyter Spark uses the existing Hive-backed Iceberg catalog and the existing `lake/warehouse` RustFS data path; it does not use Nessie.
10. The Spark authorization matrix is `user_a`: allow `databaseA`, deny `databaseB`; `user_b`: allow both databases.
11. A denied test is valid only when evidence shows the intended effective principal and an authorization decision. Authentication, session startup, missing object, Hive connectivity, and RustFS credential failures do not count as denials.
12. An unexpected allow/deny or unsupported Hive/RustFS enforcement is a failed or blocked feasibility outcome, never a reason to elevate a user or change policies automatically.

## Lifecycle and Evidence

13. Stopping or recreating a user's container destroys its ticket cache but preserves that user's work volume and all platform data/credentials.
14. No notebook work volume is shared writable across usernames. The existing sibling shared-notebook mount is not carried forward as a writable shared workspace.
15. Logs and query evidence may include usernames, principal names, requested database/table, outcome, and redacted error categories; they must not include passwords, RustFS secret keys, keytab contents, tickets, or complete credential environments.
16. The `admin` session is not substituted for the two test-user authorization scenarios.
17. JupyterHub introduces no Airflow/Jenkins integration and no direct RustFS authorization acceptance scenario.
