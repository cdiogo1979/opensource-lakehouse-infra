# Build and Test Summary — Unit 3

## Build and local checks

- **JupyterHub image:** `local/lakehouse-jupyterhub:6.1.1` built successfully.
- **Spark-enabled single-user image:** `local/lakehouse-jupyter-singleuser:6.1.1-spark` built successfully with the Unit 3 Spark source/configuration.
- **Compose:** `docker compose -f docker-compose.yml config --quiet` passed before and after runtime property preparation.
- **Static checks:** Python compilation for implementation and tests, Bash syntax for the local launcher/session scripts, and Keycloak realm-contract JSON validation passed.
- **Pure contract checks:** Role/environment/operation matrix, exact approved catalog/bucket/database/table locations, malformed/cross-environment location rejection, credential/cache invariants, and Polaris runtime property values passed.

## Tests

- **Full repository pytest suite:** 75 passed, plus 5 Hypothesis subtests; seed `20261028`.
- The host Python environment lacked pytest, Hypothesis, and Tornado, and could not reach PyPI. The pinned test-only requirements were installed in an ephemeral Hub-image container instead. The repository was mounted read-only and pytest cache was disabled. An initial collection attempt exposed the existing Hub module path requirement; the final run supplied `/etc/jupyterhub` on `PYTHONPATH` and passed.
- **Earlier source-only runs:** six Keycloak contract tests passed on the host. The host JupyterHub unittest run passed 24 tests but could not import the Tornado-dependent broker module; the final complete pytest run in the built Hub image includes those tests and passed.
- **Live role matrix:** The one-time approved verifier passed for developer, analyst, owner, and writer across production, UAT, and dev. It confirmed the expected Keycloak role claims and Polaris principal roles, expected Spark read/write allow/deny behavior, and expected table locations. All three smoke tables were restored to their original single row.
- **Temporary identity cleanup:** The verifier reported cleanup complete; both possible role-matrix credential-file paths are absent. The script removes its uniquely prefixed Keycloak clients and Polaris principals after its checks.

## Polaris runtime configuration check

- Prepared only the managed Polaris application properties in `.runtime/credentials/polaris-application.properties` and staged `.runtime/container-mounts/polaris-application.properties`. Existing protected property values were preserved; no credential values were displayed or rotated.
- **User-approved TTL amendment (2026-10-28):** storage credential duration is now 3600 seconds (one hour); cache remains 600 seconds. Polaris container properties were checked after restart and show these effective values, along with 8 pooled storage HTTP connections, PT1S acquisition/connect waits, PT2S read wait, and `quarkus.management.host=127.0.0.1`.
- Restarted only the Polaris container to load the staged file. Its container health reported `healthy` after restart. Compose continues to publish REST port 8181 only on host loopback; management port 8182 remains unpublished. The health check reaches the in-container loopback management endpoint.
- Follow-up live listener check confirmed `http://127.0.0.1:8182/q/health/ready` returns 200 inside Polaris and the same request to the container IP is refused. Docker reports only REST port 8181 published on host loopback; 8182 is not published.
- The test's temporary Keycloak clients and Polaris principal-role assignments were removed. No pre-existing user/group membership, persistent grants, RustFS policies, buckets, catalog/namespace/table metadata, or unrelated lakehouse data were changed.

## Follow-up: Polaris-vended RustFS credentials

- **Credential lifetime:** Fresh Polaris credential responses for `lakehouse`, `lakehouse_uat`, and `lakehouse_dev` each reported approximately 3599 seconds remaining, confirming the one-hour setting is accepted by the running Polaris/RustFS stack.
- **Credential scope:** Each response was used in memory only for a direct read-only object `HEAD` within its smoke-table location; all three returned HTTP 200. A production-vended credential was denied with HTTP 403 when it attempted to read a known-existing dev metadata object. Object existence was checked separately with the administrative identity. The test created or changed no objects and printed or persisted no credential values.
- **Observed response timing:** The three table credential/resource requests completed in 0.966, 0.042, and 0.040 seconds. All were below five seconds. The first followed a Polaris restart; later requests may have benefited from Polaris's 600-second credential cache. This small sample does not establish a cold-request percentile or prove a hard five-second end-to-end deadline.

## Remaining verification gaps

- The exact RustFS 1.0.4 vended credential duration and table-prefix read scope are now live-verified. Direct reads within scope succeeded and a cross-environment read outside scope was denied. Other operations (for example, listing, writes, deletes, and multipart behavior) were not individually checked.
- Actual developer/analyst authorization and allowed/denied Spark operations are now live-verified. The user confirmed that token expiry requires starting a new Spark session, verifying the expected fail-closed/restart behavior. Two-user concurrency was not exercised against the providers.
- A later Iceberg refresh uses the original 300-second user JWT. After JWT expiry, Polaris rejects refresh and Spark fails closed; the observed recovery is to start a new Spark session. Automatic in-session user-JWT renewal is not implemented.
- Configured per-stage timeouts and three observed sub-five-second requests do not prove the required strict five-second end-to-end STS deadline or a p95 latency target. DNS, scheduling, cache state, and retries can extend total latency.
- Concurrent workload and resiliency scenarios were not run and are explicitly deferred for now per user decision. The platform operator remains the owner if they are revisited; no schedule date is set. Performance/load measurements remain unverified.

The user considers Unit 3 testing complete with the limitations above recorded for follow-up. Verified results remain distinct from unverified behavior: automatic in-session user-JWT renewal, complete operation-level scope, a strict end-to-end latency bound, and performance/resiliency were not demonstrated by these tests.
