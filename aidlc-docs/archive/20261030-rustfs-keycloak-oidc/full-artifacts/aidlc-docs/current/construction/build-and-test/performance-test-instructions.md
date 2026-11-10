# Performance Test Instructions — rustfs-keycloak-oidc

**Not applicable.** The approved requirements set no performance, throughput, or latency targets for console login. The change adds an interactive login path and no data-path processing. Polaris STS vending and S3 data access are unchanged (Scenario 3 in `integration-test-instructions.md`).

Known fixed behavior: RustFS 1.0.4 issues console sessions for 3600 s. If Keycloak is unavailable, RustFS retries discovery in the background (see the business rules, BR-18).
