# Build and Test Summary — Unit 2

## Build

- **JupyterHub image:** `local/lakehouse-jupyterhub:6.1.1` built successfully from the pinned JupyterHub base image.
- **Spark-enabled single-user image:** `local/lakehouse-jupyter-singleuser:6.1.1-spark` built successfully from the pinned Spark/Iceberg and JupyterHub single-user base images.
- **Compose:** `docker compose -f docker-compose.yml config --quiet` passed.
- **Static checks:** Python compilation for the Unit 2 implementation and tests, and Bash syntax checks for `scripts/lakehouse.sh` and `start-session.sh`, passed.
- The dependency lock remains direct constraints rather than a complete transitive resolution. Image builds succeeded, but a fully reproducible locked dependency build is not established.

## Tests

- **JupyterHub suite:** 34 tests passed in the rebuilt Hub image. This includes existing Unit 1 Hub tests and Unit 2 broker, client, Spark handoff, certificate, and network contract tests.
- **Keycloak contract suite:** 6 tests passed on the host Python environment.
- An initial run found failures in test setup and Tornado request construction. The client TLS-context mocks, certificate helper path handling, and broker HTTP request/response handling were corrected; the final suite passed after rebuilding the Hub image.

## Runtime verification limits

- No Compose service was started or reconfigured. Provider identities/policies, buckets, catalogs, persistent volumes, and objects were not changed.
- Live Keycloak refresh, JupyterHub login/spawn, container network attachment, Polaris token acceptance, Spark catalog access, and RustFS credential vending were not exercised.
- Performance/load and integrated end-to-end tests remain outstanding. Treat the Unit 2 source and image builds as passed, but live integration as unverified.
- The broader Unit 1 verification waiver remains limited to its previously accepted gaps; this Unit 2 report does not extend that waiver.
