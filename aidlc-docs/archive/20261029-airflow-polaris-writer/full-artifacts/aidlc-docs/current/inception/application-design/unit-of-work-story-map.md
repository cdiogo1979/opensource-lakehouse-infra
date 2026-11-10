# Requirement-to-Unit Map — Airflow Polaris Writer Identity

User Stories was skipped for this infrastructure integration; the map assigns every approved functional and non-functional requirement directly to its owning unit and integration gate.

| Requirement | Unit 1: Airflow writer identity and broker | Unit 2: Shared Spark runtime and identity adapters | Integration / verification evidence |
|---|---|---|---|
| FR-1 Airflow deployment | Owns Compose services and Airflow/broker deployment. | Provides Spark runtime consumed by Airflow. | Airflow service health and DAG availability. |
| FR-2 Bundle contract | Preserves names, refs, and selection in Airflow integration. | Must not change Bundle behavior. | Validator confirms exactly `lakehouse-main` → `main` and `lakehouse-uat` → `uat`. |
| FR-3 Writer identity and authorization | Configures broker for the writer client. | Airflow adapter uses writer token; no identity fallback. | Main Spark run is authorized as existing `role-default-writer`; UAT mapping is source/config checked. |
| FR-4 Token acquisition and delivery | Owns secret, initial token issuance, run registration, and protected Spark handoff. | Accepts only token and run capability, never writer secret. | Secret/token handling review and broker contract checks. |
| FR-5 One-hour writer token and renewal | Sets writer broker renewal contract and bounded run capability. | Refreshes token before expiry without restarting Spark or Jupyter session. | Renewal/provider checks; main runtime run exercises writer identity. |
| FR-6 Polaris and RustFS integration | Makes broker reachable to the per-run Spark container. | Supplies current bearer to Iceberg REST; separates OAuth and vended S3 credential lifecycles. | Main run reads/writes through Polaris and Polaris-vended RustFS credentials. |
| FR-7 Production workflow | Preserves and orchestrates `main-init_environment`. | Supplies compatible runtime without workload-entrypoint changes. | Main/production E2E with existing sample-table overwrite. |
| FR-8 Release visibility | Coordinates Bundle deployment boundary. | Workload source/image reference changes are committed and pushed to workload repo `main`. | Airflow main Bundle sees the approved source commit. |
| NFR-1 Secret/token handling | Protects client secret, capability registry, TLS API, and broker logging. | Redacts tokens and keeps credentials out of logs. | Configuration/source review and test logs. |
| NFR-2 Least privilege | Uses existing writer client only. | Does not elevate identity or broaden access. | Verify role identity; no Polaris/RustFS grant mutation. |
| NFR-3 Compatibility | Preserves Bundle contract. | Pins compatible shared runtime and retains human user behavior. | Runtime compatibility and source contract checks. |
| NFR-4 Test scope and evidence | Supports main-only workflow. | Supports production runtime verification. | Main E2E; UAT source/config only; concurrent and resilience tests explicitly deferred. |
