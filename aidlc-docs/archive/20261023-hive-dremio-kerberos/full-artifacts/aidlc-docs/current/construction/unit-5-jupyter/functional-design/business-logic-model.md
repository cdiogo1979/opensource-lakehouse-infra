# Unit 5 JupyterHub and Per-User Spark — Business Logic Model

## Purpose

Provide isolated local notebook sessions for `user_a`, `user_b`, and the operator `admin`. Each session runs its own local Spark process and uses only the Kerberos principal/keytab and RustFS identity assigned to the matching username. The two test users demonstrate the same Hive database access profiles used by Dremio.

## Actors and Components

| Actor/component | Responsibility |
|---|---|
| PoC operator | Starts the existing Compose environment, opens JupyterHub on the local host, reviews session status and redacted query outcomes, and stops or recreates individual sessions. |
| JupyterHub | Accepts the three configured development labels using DummyAuthenticator, applies the `admin` Hub role, and requests a distinct single-user container for each label. |
| DockerSpawner | Creates one isolated container per username, attaches that user's work volume, and supplies only the corresponding read-only keytab and RustFS identity. |
| Single-user Jupyter/Spark session | Runs JupyterLab and local Spark; obtains a Kerberos ticket as the session user, reads Hive catalog metadata, and accesses RustFS with that user's S3 credentials. |
| Kerberos KDC | Issues a ticket for the matching provisioned principal after the session initializes from its mounted keytab. |
| Hive Metastore | Serves the `iceberg` Hive catalog and applies the configured effective-user authorization behavior. |
| RustFS | Stores Iceberg files under the existing lake warehouse; Spark connects with the matching user's named credential. |

## Session Start and Query Flow

1. The user enters one of the configured labels: `user_a`, `user_b`, or `admin`. DummyAuthenticator does not validate that the person owns the label; this is a localhost-only development mechanism.
2. Hub resolves the exact username through the approved identity map and spawns a separate single-user container. Unknown labels must not receive a credential mapping or a session.
3. The session receives its matching keytab as a read-only mount, its own private ticket-cache path, and only its matching RustFS access/secret values. Credential values are never returned to Hub logs or notebook output.
4. Session startup obtains a Kerberos ticket for the matching principal. A ticket acquisition failure prevents Spark authorization scenarios from running.
5. Local Spark uses the existing `iceberg` HiveCatalog contract, connecting to `thrift://hive-metastore:9083`, with RustFS warehouse I/O at the configured `lake/warehouse` path. It uses its isolated Kerberos cache for Hive and its matching AWS credential provider values for RustFS.
6. The user submits a direct Spark query against a sample database. The effective identity and expected policy result are recorded without secrets.
7. On logout/stop, the ticket is destroyed as part of the session lifecycle. The per-user notebook work volume remains for the next session; no other user's writable workspace is attached.

## Expected Spark Access Matrix

| Jupyter username | Kerberos principal | RustFS identity | `databaseA` | `databaseB` |
|---|---|---|---|---|
| `user_a` | `user_a@LAKEHOUSE.LOCAL` | `user_a` | Allow | Deny |
| `user_b` | `user_b@LAKEHOUSE.LOCAL` | `user_b` | Allow | Allow |
| `admin` | `admin@LAKEHOUSE.LOCAL` | `admin` | Not part of the test-user matrix | Not part of the test-user matrix |

Mark an expected denial as demonstrated only when the session identity is known and the error identifies an authorization decision. Missing tables, invalid credentials, Kerberos failures, Hive connection errors, and RustFS signature/credential errors are separate failure outcomes.

## Administrator Behavior

`admin` is a JupyterHub administrator and receives only the `admin` Kerberos and RustFS identities in its own Spark session. Hub administrator status controls Hub operations; it is not evidence of Spark database authorization and does not permit the session to borrow another user's credentials. The `admin` session is not used to satisfy `user_a` or `user_b` access checks.

## Failure and Recovery

- If the Hub is unavailable or a user server fails to start, report a session-start failure; do not launch a shared Spark fallback.
- If the keytab is missing/unreadable or Kerberos acquisition fails, stop before Hive queries and report the matching principal and failure category without exposing credentials.
- If Spark cannot reach Hive or RustFS, classify it as a dependency/connectivity failure, not an authorization denial.
- If an allowed query is denied or a restricted query succeeds, report the profile as failed and preserve state for review. Do not switch to `admin` or the writer identity.
- If Hive/RustFS cannot enforce the per-user result for this access path, record the evidence as a feasibility blocker and request review of the smallest architecture adjustment.
- Existing data, credentials, and per-user work volumes are preserved when a session stops or fails.

## Observable Outcomes

For each query attempt, record timestamp, Jupyter username, effective Kerberos principal, database/table, expected result, actual result, and a redacted failure category. Never record password/key values, keytab contents, ticket-cache contents, or credential-bearing environment dumps. Direct RustFS access is not an acceptance scenario.
