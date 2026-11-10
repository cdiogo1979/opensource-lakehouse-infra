# Domain Entities — Unit 1 Airflow Writer Identity and Broker

**Status:** Final for Unit 1 Functional Design review.

## `DagRunKey`

Identifies one Airflow DAG execution independently of task retries.

- `dag_id`: stable DAG identifier.
- `run_id`: Airflow-generated execution identifier.
- Uniqueness: `(dag_id, run_id)`.
- Task attempt/try number is metadata for logs and orchestration, not part of the renewal identity.

## `RunAuthorization`

Represents permission for one ephemeral Spark workload to renew writer access during a DAG run.

- `run_key`: associated `DagRunKey`.
- `capability_verifier`: one-way verifier of the opaque capability; raw capability is held only by Airflow protected run state and the matching Spark process.
- `idempotency_key`: stable key derived from `(dag_id, run_id)` for safe duplicate registration.
- `encrypted_capability_replay`: short-lived encrypted in-memory replay record used only when Airflow loses the initial response; removed at revocation or expiry.
- `issued_at`: registration time.
- `expires_at`: no later than the configured DAG-run maximum duration.
- `status`: `ACTIVE`, `REVOKED`, or `EXPIRED`.
- `last_renewal_at`: optional operational metadata; never includes token content.
- Persistence: short-lived in-memory broker state per approved behavior. A broker restart loses registrations and causes subsequent renewal to fail closed.

State transitions:

```text
UNREGISTERED --create/register--> ACTIVE
ACTIVE --renew--> ACTIVE
ACTIVE --DAG terminal cleanup--> REVOKED
ACTIVE --expires_at reached--> EXPIRED
REVOKED or EXPIRED --renew--> rejected
```

Registration for the same active run is idempotent. It does not create a second capability or extend `expires_at` beyond the configured run maximum.

## `AccessToken`

A Keycloak-issued bearer JWT used by Spark for Polaris REST requests.

- `value`: secret JWT; held in protected per-run transport and Spark process memory only.
- `subject/client`: `write-service-account` service identity.
- `issued_at` and `expires_at`: validated from token claims and broker response.
- `lifetime`: one hour, configured for the writer service account only.
- Persistence: not stored in broker registration state or durable logs.

## `SparkTokenState`

Per Spark application state owned by the shared provider.

- `current_token`: current validated `AccessToken` in process memory.
- `renewal_adapter`: explicit `AirflowWriterAdapter` for Unit 1; Jupyter uses its separate adapter.
- `renewal_capability`: opaque run capability, scoped to one `DagRunKey`.
- `refresh_lock`: coordinates concurrent requests in that Spark process so only one refresh replaces the token at a time.
- `refresh_status`: idle, refreshing, usable, or failed.

A token replacement is accepted only after identity/expiry validation and updates `current_token` atomically for subsequent requests.

## `DAGRunAttempt`

An Airflow task attempt associated with a stable `DagRunKey`.

- `try_number`: Airflow retry count.
- `spark_container`: the process/container associated with the attempt.
- `run_authorization`: reference to the DAG-run-scoped authorization, reused across attempts.

A failed attempt may be cleaned up and retried without changing the run key or capability. Terminal DAG cleanup revokes the shared authorization and removes any remaining run container.

## Relationships

```text
DagRunKey 1 ── 1 RunAuthorization
DagRunKey 1 ── * DAGRunAttempt
DAGRunAttempt * ── 1 RunAuthorization
DAGRunAttempt 1 ── 1 SparkTokenState (while its Spark process is active)
SparkTokenState 1 ── * AccessToken (sequential replacements; one current at a time)
```
