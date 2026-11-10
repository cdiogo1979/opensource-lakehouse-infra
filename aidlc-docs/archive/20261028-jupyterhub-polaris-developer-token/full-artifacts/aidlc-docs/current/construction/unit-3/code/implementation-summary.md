# Unit 3 Code Generation — Implementation Summary

## Outcome

Source implementation and focused test sources have been generated for the approved Unit 3 scope. No test, image build, runtime preparation, Compose operation, service restart, or provider mutation was performed in this stage. The active `.runtime` files and all running provider state were left untouched.

## Generated changes

| Area | Files | Result |
|---|---|---|
| Polaris runtime config | `infra/polaris/oidc.properties`; `scripts/prepare-lakehouse-runtime.py` | User-approved follow-up amendment on 2026-10-28 sets Polaris 1.8.0 credential/cache targets to 3600/600 seconds. Also sets Quarkus management listener host `127.0.0.1`, max 8 pooled storage HTTP connections, and connection-acquisition/connect/read limits of 1/1/2 seconds. Runtime generation validates positive timing values and a cache shorter than the credential lifetime; managed-property merge and protected-value output remain intact. |
| Authorization and path oracle | `infra/spark-bootstrap/verify_role_matrix.py` | Added a pure approved role/environment oracle and exact catalog-to-bucket/database path resolver in the existing verifier. Live role-matrix verification now checks readable table locations against the expected `bucket/catalog/db/table` path. Spark is imported only when the verifier starts a Spark session, so pure contract helpers can be imported in unit tests. |
| Spark token contract | `infra/jupyter/singleuser/lakehouse_spark.py` | Kept the exact broker-issued user access JWT in Spark's in-memory Polaris configuration and kept OAuth token refresh disabled. Added a code comment distinguishing OAuth token renewal from Iceberg's separate S3 vended-credential refresh endpoint. No static storage credential fallback was added. |
| Focused tests | `tests/polaris/test_unit3_runtime_config.py`, `test_unit3_authorization_properties.py`, `test_unit3_location_properties.py`, `test_unit3_runtime_properties.py`, `test_unit3_compose_contract.py`; `tests/jupyterhub/test_unit3_spark_credential_refresh.py`; `tests/requirements-pbt.txt` | Added named regression checks and Hypothesis properties for role union/deny-by-default, analyst read-only behavior, developer environment limits, independent approved catalog/bucket mapping, exact storage paths, traversal/duplicate/cross-bucket rejection, credential/cache bounds, generated Polaris properties, Compose isolation, and separation of user JWT from vended storage credential refresh. Test-only pins: pytest 9.2.0, Hypothesis 6.170.12, and Tornado 6.5.2. |
| CI | `Jenkinsfile` | Added a Python 3.11+ test stage that installs test-only dependencies, runs the repository pytest suite with the Jenkins build number as Hypothesis seed, and archives the seed and test log. It has no deployment or service-management stages. |
| Operator guidance | `README.md` | Clarified that Spark's OAuth token is not renewed by Iceberg's independent S3 credential refresh and that an expired user JWT fails closed; a new Spark session obtains a fresh identity token. |

## Compatibility evidence and limits

| Topic | Evidence / result |
|---|---|
| Polaris credential duration/cache properties | The [Polaris 1.8.0 configuration reference](https://polaris.apache.org/releases/1.8.0/configuration/configuration-reference/) defines `polaris.features."STORAGE_CREDENTIAL_DURATION_SECONDS"` and `...CACHE_DURATION_SECONDS` as integer seconds and requires the cache to be shorter than credential duration. The amended source template sets 3600 and 600. Build and Test confirmed the running container settings and approximately 3599 seconds returned for each of the three catalogs. |
| Polaris management host | [Quarkus 3.20](https://quarkus.io/version/3.20/guides/management-interface-reference/) supports `quarkus.management.host`; the source template sets `127.0.0.1`, keeps Compose port 8182 unpublished, and retains the in-container health check. The actual listener binding and health behavior remain a pinned-image runtime check. |
| Polaris storage connection limits | Polaris 1.8.0 documents `max-http-connections`, `connection-acquisition-timeout`, `connect-timeout`, and `read-timeout`. Configured bounds are 8 connections and PT1S/PT1S/PT2S. The [reference](https://polaris.apache.org/releases/1.8.0/configuration/configuration-reference/) documents per-stage limits, not one strict end-to-end request deadline. The approved five-second end-to-end STS target is therefore not claimed as enforced; DNS, retries, scheduling, and other work can extend total time. |
| RustFS STS duration and scope | RustFS's [IAM documentation](https://docs.rustfs.com/en/security-compliance/iam) does not establish the exact behavior of the locally pinned RustFS 1.0.4 build. Live checks now confirmed approximately one-hour Polaris-vended credentials, successful read-only access within each smoke-table location, and HTTP 403 for a production credential reading a known-existing dev metadata object. This verifies sampled read scope, not every S3 operation or every resource. |
| Iceberg 1.8.1 credential refresh | The [Polaris vended-credentials guide](https://polaris.apache.org/releases/1.8.0/vended-credentials/) documents the REST refresh endpoint and Apache Spark/Iceberg 1.8+ compatibility. Iceberg 1.8.1's upstream [`VendedCredentialsProvider`](https://github.com/apache/iceberg/blob/apache-iceberg-1.8.1/aws/src/main/java/org/apache/iceberg/aws/s3/VendedCredentialsProvider.java) uses the configured OAuth bearer token for refresh and prefetches credentials before expiration. It is a distinct path from Iceberg OAuth token refresh, which this project disables to retain the original user identity. |
| User-token lifetime | The approved Keycloak realm contract issues human access JWTs for 300 seconds. A later credential-refresh request reuses that original token; after it expires, Polaris rejects refresh and the operation fails closed. Long-lived Spark sessions therefore need a new session after user-token expiry. There is no in-session user-token renewal in the current broker/Spark contract. |
| Retry and total deadline | No application retry or total-deadline wrapper was added: the pinned configuration reference only established per-stage storage-client waits, and automatic mutation replay is prohibited. A strict five-second total deadline and exactly-one-safe-read retry remain unverified implementation gaps for review/Build and Test. |

## Security and behavior boundaries

- Existing role grants, Keycloak identities/groups, catalogs, buckets, objects, and runtime secrets were not changed.
- Spark receives no RustFS root, bootstrap, or writer credentials. No shared-user fallback was introduced.
- The management listener remains container-loopback-only by source configuration and has no host port publication; actual reachability has not been exercised.
- Role/path properties here validate local pure logic and expected mappings. They do not prove Polaris authorization decisions or RustFS STS scoping.
- Temporary credentials, JWTs, secret values, and query contents are not added to logs or test fixtures.

## Test and build status

Tests and CI configuration are source-only at this gate. No tests were run, no Jenkins build was triggered, no image was built, and no runtime property file was prepared. Build and Test must execute the new and existing test suite, render Compose, build only if the approved build plan calls for it, and verify the effective Polaris listener/settings and RustFS scope before treating compatibility as passed.

## Resiliency compliance and handoff

The current Unit 3 design artifacts do not define the individual text for `RESILIENCY-01` through `RESILIENCY-15`; assigning separate meanings to those numbers would invent requirements. The following available local-profile controls are implemented in source or explicitly identified as gaps:

| Control area | Status |
|---|---|
| Bounded storage pool and connection-stage waits | Implemented in source config; effective runtime behavior unverified. |
| Authorization/credential failures fail closed; no static-key fallback | Preserved by the approved functional rules and source config; external behavior unverified. |
| Safe-read-only retry; ambiguous mutation no replay | No new retry wrapper added; Spark/Iceberg default retry behavior remains to be inspected. |
| Strict five-second end-to-end STS deadline | Gap remains: three observed credential/resource requests completed in 0.966, 0.042, and 0.040 seconds, but the sample is too small and may include cache hits. No documented single deadline knob was found in pinned Polaris config; per-stage waits are not equivalent to an end-to-end deadline. |
| Health and management isolation | Existing health check retained; loopback binding configured, runtime reachability unverified. |
| Production HA, multi-zone/region, autoscaling, DR, production SLA/RTO/RPO, backup/replication, rollout/rollback, formal change management, production incident response | N/A for the approved local proof-of-concept. |

Deferred resiliency scenarios for the validation handoff: Keycloak/JWKS outage; Polaris outage; RustFS STS timeout/pool saturation; expired vended credential; refresh denial; ambiguous mutation outcome. **Owner:** platform operator. **Scheduled date:** not set; record one before the separately scheduled resiliency validation. No chaos or DR test was run in this generation stage.

## Traceability

| Story | Generated support | Remaining evidence |
|---|---|---|
| US-04 — developer reads all environments and mutates dev only | Role oracle, path map, verification path assertion, property and example tests | Execute unit tests and live role/path/credential checks. |
| US-05 — analyst reads production only and never mutates | Role oracle, analyst deny-write properties/examples, path mapping | Execute tests and live analyst access checks using an already approved identity. |
| US-06 — operator diagnoses without credential exposure | Static/redacted runtime diagnostic, no-secret tests, Compose boundary tests, README behavior notes | Inspect runtime logs and endpoint isolation in Build and Test; verify actual credential refresh/rejection. |

This summary advances only Unit 3 Code Generation. Build and Test and Deploy Handoff remain separate approval gates.
