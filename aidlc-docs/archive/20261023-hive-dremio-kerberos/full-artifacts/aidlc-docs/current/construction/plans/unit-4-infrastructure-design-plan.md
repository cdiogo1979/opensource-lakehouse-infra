# Infrastructure Design Plan — Unit 4: Dremio Source and Query Identity

## Scope

Map Unit 4's Dremio query identities, Hive impersonation path, authorization checks, and local evidence to the existing Docker Compose deployment. Unit 4 is an operator-invoked verification flow over the current services; no new runtime services, published ports, volumes, or network are planned. This stage documents infrastructure boundaries and does not modify runtime configuration.

## Infrastructure design checklist

- [x] Confirm the deployment target and reuse of the existing Compose project/network.
- [x] Map query execution and Dremio local-user credentials to existing compute/services and protected runtime files.
- [x] Confirm metadata/storage dependencies and persistent-state preservation.
- [x] Confirm that no messaging or asynchronous infrastructure is required.
- [x] Confirm network exposure, monitoring/logging, and shared-resource boundaries.
- [x] Resolve all answers and produce deployment architecture artifacts.

## Existing infrastructure contracts

- Dremio Community 26.0.5, Hive Metastore 3.1.3, Kerberos KDC, PostgreSQL metadata store, RustFS, and Spark run in the existing `iceberg_net` Compose network.
- Dremio, Hive, KDC, PostgreSQL, RustFS, and sample-data volumes/configuration remain in place.
- Existing host ports are loopback-bound. Unit 4 adds no service or host port.
- Dremio's local test users need separate protected local passwords. The Hive source continues to use its Dremio Kerberos service identity and existing RustFS writer credential.
- Query checks are serial and operator invoked. Results/log excerpts remain local and redacted.
- No availability SLA, scale target, message queue, separate audit store, or monitoring service is approved.

## Current Status

Unit 4 NFR Design was approved by the user on 2026-10-23. The user selected A for all seven infrastructure questions. Infrastructure artifacts are complete and ready for review. The RustFS writer credential and all runtime configuration remain unchanged.
