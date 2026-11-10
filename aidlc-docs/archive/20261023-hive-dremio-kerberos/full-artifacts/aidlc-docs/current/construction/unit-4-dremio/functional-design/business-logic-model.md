# Unit 4 Business Logic Model — Dremio Query Identity

## Purpose

Unit 4 verifies that Dremio queries use the intended Hive identity and that Hive authorization produces the approved database access profile. Dremio connectivity and successful reads under the source's configured RustFS credentials are prerequisites, not authorization proof.

## Query flow

1. A test user authenticates to Dremio with that user's own local Dremio account.
2. The Dremio Hive source authenticates to Hive Metastore using the configured `dremio@LAKEHOUSE.LOCAL` service principal.
3. The source's Storage Based with User Impersonation mode passes the Dremio query username as the impersonated Hive username. The mapping is identity-preserving: `user_a` → `user_a`; `user_b` → `user_b`.
4. Hive Metastore applies its configured storage-based authorization checks to the requested database/table metadata and relevant storage paths.
5. Dremio returns the query result or a denial. The verification record distinguishes a Hive authorization denial from Dremio source/Space permissions, authentication failures, and storage credential errors.

## Required outcomes

| Dremio user | Hive effective user | `databaseA` | `databaseB` |
|---|---|---|---|
| `user_a` | `user_a` | Allow | Deny |
| `user_b` | `user_b` | Allow | Allow |

Direct queries against Hive source tables are the primary evidence. Queries through the existing Dremio Space views are secondary evidence and must preserve the query user's identity with VDS-based Access Delegation disabled.

## Failure behavior

- Missing local Dremio user or invalid credentials: stop that user's scenarios; do not substitute `admin` or `write-service-account`.
- Proxy-user or effective-identity mismatch: mark the scenario failed and preserve logs with secrets redacted.
- Missing Hive storage-based authorization or a RustFS permission model that cannot distinguish users: mark the matrix unverified/blocked. Preserve current data and credentials and present the smallest architecture adjustment for review.
- A Dremio Space permission denial does not count as a Hive authorization denial.
- An S3 credential error does not count as a database authorization denial.

## Evidence record

For each attempt, record timestamp, Dremio username, requested source path/database/table, expected result, actual result, effective Hive username evidence, denial component/error category, and whether a result row was returned. Never include passwords, keytabs, ticket contents, or S3 key values.
