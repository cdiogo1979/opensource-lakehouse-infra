# Unit 5 Logical Components — JupyterHub and Per-User Spark

Unit 5 uses the approved local Compose project and existing platform services. No additional runtime, observability, scheduling, cache, or authorization component is introduced.

| Component | Responsibility | Boundary and evidence |
|---|---|---|
| JupyterHub 5.3.0 | Bind to the local host, accept only `user_a`, `user_b`, and `admin` labels through DummyAuthenticator, apply the Hub admin role to `admin`, and coordinate per-user servers. | Usernames are not verified identities. The Hub alone receives the Docker socket needed by DockerSpawner. No remote exposure is permitted. |
| DockerSpawner | Create and stop one single-user container per username; attach that username's persistent work volume, read-only keytab, and matching RustFS identity. | Spawn failures are isolated to the requested session. No queue, preemption, automatic retry, or cross-user fallback is provided. |
| Single-user Jupyter/Spark container | Run JupyterLab and local Spark as non-root `jovyan`; hold the matching session ticket cache and credentials; run direct Hive-backed Spark queries. | No Docker socket, privileged mode, shared writable workspace, or other user's credential is mounted. A session failure does not stop other containers. |
| Kerberos KDC | Issue a ticket for the principal associated with the Jupyter username. | The notebook container uses its matching read-only keytab and private ticket cache. The cache is destroyed when the container stops. |
| Hive Metastore | Serve the existing Hive Iceberg catalog and make authorization decisions for the effective session identity. | Authentication/connectivity failures and Hive authorization decisions are reported as distinct categories. Actual cross-engine enforcement remains a runtime feasibility gate. |
| RustFS | Store the existing Iceberg table files and accept the session's matching RustFS identity for Spark I/O. | The per-user credential is used by Spark; direct RustFS authorization is not an acceptance test. |
| Per-user work volume | Persist one user's notebooks and work files across stop/recreate of that user's container. | Each username has a separate writable volume. No shared writable notebook mount or automatic backup/restore is provided. |
| Local operator and evidence | Observe container/log status, diagnose failures, restart one affected session, and retain minimal redacted query outcomes. | No monitoring service or centralized audit store. Evidence excludes credentials and ticket contents. |

## Session Interaction

`local user label` → `JupyterHub` → `DockerSpawner` → `isolated Jupyter/Spark container` → `Kerberos KDC + Hive Metastore + RustFS`

The user container uses the same-name Kerberos and RustFS identities. The operator handles failures and reviews local redacted evidence. A resource or service failure is not interpreted as a policy denial.
