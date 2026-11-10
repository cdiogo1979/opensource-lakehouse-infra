# Business Rules — Unit 1 Airflow Writer Identity and Broker

**Status:** Final for Unit 1 Functional Design review.

## Identity and authorization

1. Airflow Spark authenticates to Polaris as Keycloak confidential client `write-service-account`.
2. Polaris remains the policy decision point and authorizes using the existing `role-default-writer` role; Unit 1 does not add or broaden grants.
3. The writer client access token has the approved one-hour lifespan. Human JupyterHub token lifetimes and user authorization remain unchanged.
4. Missing, invalid, expired, revoked, or mismatched run authorization fails closed. No fallback identity or privileged credential is permitted.

## Client secret and token handling

5. The client secret is readable only within the Airflow broker's protected trust boundary. It is never returned by an API, mounted into Spark, passed to Jupyter, included in Spark environment variables, or written to logs.
6. The initial access JWT and renewal capability are separate per-run values. Only the matching Spark run receives them via the approved protected handoff.
7. The broker returns the access JWT and absolute expiry; the client validates the token expiry and rejects malformed responses. Tokens and capabilities are redacted from logs, diagnostics, and exception text.
8. Issued JWTs are self-contained: revoking the broker capability blocks renewal but does not revoke an already-issued JWT at Polaris. The JWT remains usable only until its one-hour expiry, subject to Polaris authorization.

## Run registration and capability

9. Authorization is scoped to the stable `(dag_id, run_id)` pair. Airflow task retries within that DAG run reuse the same capability.
10. Registration uses a stable idempotency key derived from `(dag_id, run_id)`. For an active run, a duplicate registration returns the same capability and a fresh initial JWT; it must not silently rotate or broaden the run capability.
11. The broker stores a one-way verifier/hash of the high-entropy capability. It may additionally keep a short-lived encrypted in-memory replay record of the capability solely to recover a lost initial response; remove that record on run revocation or expiry.
12. The broker rejects a capability for a different run, an expired run, a revoked run, or a run beyond its configured maximum duration.
13. The capability expiry is no later than the Airflow run's configured maximum duration. If the run is terminal, Airflow revokes it and removes the associated Spark container on all outcomes.
14. If broker state is lost on broker restart, renewal fails closed; the current JWT may be used until expiry, then the Spark operation fails and Airflow cleans up. Durable recovery is not required by this unit's approved scope.

## Renewal and failure handling

15. Spark requests renewal when five minutes or less remain on the current JWT.
16. A refresh uses at most three total requests: one initial request plus two retries, with waits of one second and two seconds.
17. A retry is not started if the current JWT has 60 seconds or less remaining. If renewal cannot complete while the current JWT remains usable, fail with a sanitized authentication error; do not send an expired JWT.
18. A replacement JWT must represent the same writer client identity and pass structural/expiry validation before atomic replacement in the Spark process.
19. Temporary Keycloak/broker failures never cause identity switching or use of long-lived credentials. Renewal responses do not include the client secret.
20. Polaris-vended RustFS credentials are distinct from OAuth JWTs; success or renewal of one credential type does not imply validity of the other.

## Preserved workload behavior

21. Bundle names, tracking refs, directories, and selection behavior remain unchanged: `lakehouse-main` → `main`; `lakehouse-uat` → `uat`.
22. The production test remains the existing `main-init_environment` workflow and its configured sample-table overwrite. UAT runtime, concurrent-workload, and resilience tests remain excluded.
