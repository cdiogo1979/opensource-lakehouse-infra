# Unit 2 Code Generation Summary — Hub Token Broker and Spark Identity

## Generated behavior

- The Hub runs a second Tornado HTTPS listener on its stable `jupyter-user` address, port 8443. Compose does not publish this port.
- The broker validates the caller's Hub server API token against Hub's API-token table and active spawner, derives the user/server binding from Hub state, checks the user's stored Keycloak group admission, and returns only that user's access JWT and expiry.
- The broker reuses a JWT only when more than 60 seconds remain. It serializes refresh per user, re-reads encrypted auth state after lock acquisition, applies a five-second no-replay refresh/userinfo deadline, persists rotated credentials before membership revalidation, and fails closed when rotation/admission cannot be confirmed.
- The broker emits safe correlated outcome logs and process-local aggregate counters. Its health endpoint is served on the internal TLS listener; the Hub healthcheck verifies both Hub and broker readiness.
- Host startup prepares or validates a private CA and `DNS:jupyterhub` server identity, checks file modes/chain/SAN/expiry/key match, and rejects subnet conflicts before Compose. Rotation is explicit. The signing key stays on the host; only the server key/certificate reach Hub, and user servers receive the public CA read-only.
- A new Spark session obtains the bound user's current access JWT over verified HTTPS and applies it to the Polaris Iceberg REST catalog in memory. It disables token refresh within an existing session, redacts token-like configuration, and does not expose the token through the session factory return value.

## Added files

- `infra/jupyter/hub/lakehouse_token_broker.py`
- `infra/jupyter/hub/lakehouse_jupyterhub.py`
- `infra/jupyter/hub/healthcheck.py`
- `infra/jupyter/singleuser/lakehouse_broker_client.py`
- `infra/jupyter/singleuser/lakehouse_spark.py`
- `scripts/prepare-jupyterhub-broker-certificates.py`
- `scripts/check-jupyter-user-network.py`
- `tests/jupyterhub/test_unit2_token_broker.py`
- `tests/jupyterhub/test_unit2_broker_client.py`
- `tests/jupyterhub/test_unit2_infrastructure_contract.py`

## Updated files

- `infra/jupyter/hub/Dockerfile`, `infra/jupyter/hub/jupyterhub_config.py`, and `infra/jupyter/hub/lakehouse_spawner.py`
- `infra/jupyter/singleuser/Dockerfile` and `infra/jupyter/singleuser/spark-defaults.conf`
- `docker-compose.yml`, `.env.example`, `scripts/lakehouse.sh`, and `README.md`
- `aidlc-docs/current/aidlc-state.md`, `aidlc-docs/current/audit.md`, and the Unit 2 Code Generation plan

## Traceability

- **US-03:** The supported Spark factory gets the current Keycloak access identity for the user's active Jupyter server and creates a new identity-bound Spark session.
- **US-06:** Hub owns token validation and refresh; caller-supplied identity fields are ignored; failures are correlated and logs avoid credential values.
- **FR-3:** The Hub retains confidential-client and refresh credentials and exposes only a bound access token.
- **FR-4 client handoff:** The single-user container sends its Hub server token over verified TLS and places the returned access JWT only in the Spark session's in-memory Polaris catalog configuration.
- **FR-7:** User-server isolation and internal-only broker reachability are preserved; no shared service identity or long-lived RustFS root credentials are introduced.
- **NFRs:** The source implements the approved refresh margin, per-user serialization, five-second bounded refresh, verified TLS, safe failures, and bounded logs/counters. Runtime latency and operational behavior remain to be measured in Build and Test.

## Verification boundary and remaining work

- The focused JupyterHub suite passed 34 tests, including broker ownership/refresh coordination, Spark client handoff, certificate lifecycle, network contracts, and existing Unit 1 Hub checks. The separate Keycloak contract suite passed 6 tests.
- Both pinned JupyterHub and Spark-enabled single-user images built successfully. Compose rendering, Python compilation, and shell syntax checks passed. See `aidlc-docs/current/construction/build-and-test/unit-2-build-and-test-summary.md` for command details and limits.
- No provider services were started or reconfigured, and no provider identities/policies, buckets, catalogs, or data were changed.
- The complete transitive Hub dependency lock remains unresolved; the build used the existing direct-constraint file and does not prove a reproducible locked supply chain.
- Broker-to-live-Keycloak and Spark-to-Polaris integration, live spawner/network behavior, performance, and end-to-end authorization remain unverified. These require a separate runtime verification stage; successful source tests and image builds do not establish integrated behavior.
- The broker rechecks current group admission from Hub's encrypted auth state on each request. It does not poll Keycloak for immediate group changes; existing sessions continue to use their established identity until stopped or expired.
- The local browser and Keycloak callback endpoints remain HTTP on loopback; this configuration is not intended for external exposure.
