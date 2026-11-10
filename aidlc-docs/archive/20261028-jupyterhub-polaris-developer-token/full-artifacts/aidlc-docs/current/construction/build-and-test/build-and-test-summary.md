# Build and Test Summary — Current Intent

## Current outcome: Unit 4 — testing complete; limitations recorded

- **Builds:** `local/lakehouse-jupyterhub:6.1.1` and `local/lakehouse-jupyter-singleuser:6.1.1-spark` built successfully.
- **Compose and static checks:** Compose configuration, Python compilation, Bash syntax, and Keycloak realm-contract JSON validation passed.
- **Automated tests:** 82 passed, 1 skipped, and 5 Hypothesis subtests passed. The skipped case is the explicitly opt-in provider-mutating live role-matrix wrapper; its underlying role matrix passed during Unit 3 under the one-time test authorization.
- **Final JupyterHub regression suite:** 38 tests passed inside the built Hub image after runtime corrections. Final Compose validation passed.
- **Live end-to-end:** Keycloak authorization-code login, Polaris principal reconciliation, isolated Jupyter server spawn, Spark reads from production/UAT/dev, dev write success, and production/UAT write denial all passed. The temporary user, Polaris principal, probe row, server, home volume, and Hub auth state were removed.
- **Runtime:** The latest recorded run found Keycloak, Polaris, RustFS, both databases, and JupyterHub healthy, with JupyterHub running on loopback.
- **User confirmation:** The user completed the GUI browser test and confirmed the expired Keycloak JWT requires a new Spark session. Tests and live checks also confirmed home-volume persistence, analyst production-only authorization, one-hour Polaris credentials, and sampled RustFS scope.
- **Accepted limitations:** Other S3 operations and broader scope cases were not tested; automatic in-session JWT renewal is not implemented; a strict five-second end-to-end STS deadline/p95 is not established; concurrent Spark workload/performance tests were deferred; resiliency validation has no schedule; complete dependency locking/security scanning remains open.
- **Status:** The user considers Build and Test complete with these limitations recorded. They are not reported as passed. No additional tests are required to close this testing stage.

See [Unit 4 Build and Test details](unit-4-build-and-test-summary.md), [Unit 3 results](unit-3-build-and-test-summary.md), [Unit 2 results](unit-2-build-and-test-summary.md), and [Unit 1 results and explicit waiver](unit-1-build-and-test-summary.md) for evidence by stage.

## Known dependency reproducibility limitation

The Hub requirements lock contains direct constraints but does not capture the complete resolved transitive environment. Image builds passed, but this does not establish a fully reproducible dependency supply chain. Keep this limitation open for the appropriate handoff/release decision.
