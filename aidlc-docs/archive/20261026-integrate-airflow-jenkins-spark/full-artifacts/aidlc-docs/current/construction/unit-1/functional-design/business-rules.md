# Business Rules — Spark Writer Runtime

## Identity and Credential Rules

1. The Kerberos identity is the existing `write-service-account@LAKEHOUSE.LOCAL`; do not create, rotate, or substitute a principal in this unit.
2. The keytab is an input credential and is not copied into the ticket cache, logs, Spark configuration, or workload bundle.
3. The service ticket cache is private runtime state, separate from the Airflow driver cache and notebook-user caches.
4. Hive Metastore access uses Kerberos. RustFS access uses the existing file-backed writer S3 credentials; the two mechanisms are independent.
5. The writer identity is shared by workloads on the existing Spark worker service. It is not per-author delegation and must not be described as such.

## Readiness and Admission Rules

1. A valid TGT for the configured writer principal is required before the Spark worker is ready to accept new ETL workloads.
2. If bootstrap cannot acquire or validate the TGT, the worker remains unavailable for ETL and emits a clear diagnostic without secret material.
3. A ticket that is expired, belongs to another principal, or cannot be validated does not satisfy readiness.
4. While unavailable, new writer ETL work is not admitted. Recovery requires successful acquisition and validation of a valid TGT.

## Renewal and Recovery Rules

1. Maintain the ticket before it becomes unusable; NFR Design defines exact timing and retry parameters.
2. If ticket renewal fails, attempt to acquire a fresh TGT from the existing keytab.
3. If renewal and reacquisition both fail, transition to unavailable and prevent new ETL admission. Never silently treat an expired or invalid ticket as ready.
4. A later successful reacquisition may restore readiness. NFR Design defines retry/backoff and health reporting details.
5. Credential failures must not trigger destructive actions against catalog metadata, RustFS objects, named volumes, or existing key material.

## In-Flight Work Rules

1. Losing ticket readiness does not itself trigger deliberate termination of already-running Spark workloads.
2. Each in-flight Hive or RustFS operation succeeds or fails according to the credential accepted by that endpoint at operation time.
3. New-work admission remains blocked until valid ticket readiness is restored.
4. Do not claim that successful RustFS authentication proves Hive authorization, or vice versa.

## Diagnostics Rules

- Diagnostics may identify the principal name, lifecycle state, and sanitized failure category.
- Diagnostics must not include keytab bytes, passwords, RustFS secret values, Kerberos ticket contents, or credential-bearing command output.
- Functional state is separate from operational health-check implementation; Infrastructure/NFR Design define its concrete representation.
