# Airflow Workload Execution and Writer Identity

## Execution contract

1. Airflow resolves a run against the pinned checkout from the approved production or UAT Git Bundle.
2. The Airflow broker acquires the writer service token and associates it with a unique DAG run. It keeps the Keycloak writer secret and issues a high-entropy, run-scoped renewal capability.
3. Airflow starts one ephemeral Spark container for that run, mounting the selected workload bundle read-only and passing only the initial access token, broker endpoint/CA, run handle, and renewal capability.
4. The shared Iceberg `AuthManager` uses the Airflow adapter to renew the bearer token through authenticated TLS before Iceberg REST requests. The broker owns token acquisition; Spark never receives the writer secret.
5. Spark sends the current token to Polaris for catalog operations. Polaris enforces its existing writer role and vends scoped RustFS credentials for storage access.
6. Airflow stops/removes the Spark container and revokes broker run state on completion/failure. Broker state has bounded expiry as a fallback.

## Identity and configuration rules

- Writer identity: Keycloak `write-service-account`, mapped to Polaris `role-default-writer`.
- Shared runtime: Spark 3.5.5, Java 17, Iceberg 1.10.2.
- Production Bundle: `lakehouse-main` / `main`; UAT Bundle: `lakehouse-uat` / `uat`.
- The Jupyter adapter remains user-bound and separate from the Airflow writer adapter.
- Never pass writer client secrets to Spark or log tokens, capabilities, authorization headers, or sensitive broker responses.
- Do not broaden Polaris grants or replace Polaris-vended storage credentials with RustFS root keys.

## Failure behavior and verification record

Broker registration or renewal failures fail the task/job; there is no fallback identity. Container startup failure triggers cleanup and broker revocation, with bounded capability expiry as a fallback. The DAG's cleanup path runs regardless of workload outcome.

Builds, automated checks, and the designated main production E2E passed. The user later confirmed the image build and successful main and UAT DAG runs; run IDs/revisions could not be retrieved from the active CLI session. Concurrency, resilience, and live role-matrix checks remain unverified and were outside the approved intent scope.
