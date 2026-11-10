# Functional Design Plan — Unit 1: Compose, Catalog, Identity Foundation, and Storage

## Scope

This plan covers Unit 1's Compose/lifecycle, Hive Metastore and PostgreSQL metadata store, Kerberos KDC foundation, RustFS/bucket initializer, and Hive-owned authorization behavior. It defines functional workflows and rules only; exact images, Compose syntax, ports, healthchecks, credentials mounting, and network/volume configuration belong in Infrastructure Design.

Primary stories: US-CAT-01, US-AUTH-01, and US-DOC-01. Related stories: US-ID-01 and the foundation dependencies of US-CAT-02, US-ID-03, US-JH-01, US-AUTH-02, and US-AUTH-03.

## Technical Evidence and Design Constraints

- Apache Hive documents Metastore storage-based authorization as checking filesystem permissions for database/table paths; read checks include database and table metadata lookup operations. The exact compatibility of this model with the PoC's S3-compatible RustFS paths and both Spark and Dremio clients is not established. See [Hive Metastore Storage-Based Authorization](https://cwiki.apache.org/confluence/display/hive/storage%2Bbased%2Bauthorization%2Bin%2Bthe%2Bmetastore%2Bserver).
- Apache Hive documents SQL-standard authorization as a HiveServer2 query authorization mode. The guide describes restricting clients to HiveServer2 because direct CLI/filesystem-capable clients can bypass SQL authorization checks. The approved baseline excludes HiveServer2 and includes Dremio's Hive Metastore access path, so adding HiveServer2 alone must not be assumed to enforce both query paths. See [Hive Authorization](https://cwiki.apache.org/confluence/display/Hive/LanguageManual+Authorization) and [SQL Standard Based Hive Authorization](https://cwiki.apache.org/confluence/display/Hive/SQL%2BStandard%2BBased%2BHive%2BAuthorization).
- Approved scope requires `write-service-account` to create/populate the two databases and requires `user_a`/`user_b` to receive different read outcomes through Dremio and Jupyter Spark. Any architecture change remains subject to user review.

## Functional Design Checklist

- [x] Review Unit 1 definition, story map, requirements, reverse-engineering artifacts, and approved knowledge inventory.
- [x] Confirm functional setup and lifecycle decisions from the answers below; resolve any ambiguity.
- [x] Define the initialization workflow and service/component responsibilities.
- [x] Define Hive database/table authorization behavior and the RustFS path permission relationship, including feasibility limits.
- [x] Define persistence and repeat/cleanup behavior for fresh and existing Compose state.
- [x] Define required failure outcomes for incomplete initialization and dependent services.
- [x] Generate `aidlc-docs/current/construction/unit-1-foundation/functional-design/business-logic-model.md`.
- [x] Generate `aidlc-docs/current/construction/unit-1-foundation/functional-design/business-rules.md`.
- [x] Generate `aidlc-docs/current/construction/unit-1-foundation/functional-design/domain-entities.md`.
- [x] Validate consistency with approved requirements and Unit 1 boundaries.

## Extension Compliance Summary

- **Security Baseline**: N/A — disabled by user choice; approved functional security requirements are represented in the rules and authorization feasibility gate.
- **Property-Based Testing (Partial)**: N/A for this design artifact stage; no code was introduced. Reassess applicable logic during later code planning.
- **Resiliency Baseline**: N/A — disabled by user choice. Functional failure and recovery behavior is defined from the approved scope.

## Design Questions

### Question 1 — Database authorization with the no-HiveServer2 baseline

Which authorization direction should Unit 1 design evaluate?

A) Retain standalone Hive Metastore with no HiveServer2 and evaluate Metastore storage-based authorization against RustFS paths for the Spark and Dremio client identities. If it cannot enforce both required access profiles, treat this as a blocker and return evidence plus the smallest adjustment for review (recommended; preserves approved scope).

B) Investigate HiveServer2 and/or another authorization enforcement component as a proposed architecture adjustment. Do not include it in implementation until a revised scope is approved.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 2 — Writer ownership and test-user grant timing

How should Unit 1's functional rules express the grant sequence around ETL?

A) `write-service-account` creates and owns the sample Hive databases/tables. Provision only its required create/write rights before ETL; apply `user_a`/`user_b` read grants after the databases exist, through the component-owned authorization mechanism (recommended; follows the approved ETL identity and avoids asking the service account to grant reader permissions).

B) Use `admin` to create databases or tables and let the writer only populate data.

X) Other (describe after `[Answer]:`)

[Answer]: A

### Question 3 — Initialization repeat behavior

What should happen if initialization is run when named volumes already contain Hive metadata or RustFS data?

A) Support safe reruns that preserve existing data and report already-initialized resources; never drop tables or overwrite data implicitly (recommended; supports local iteration safely).

B) Support clean deployments only; detect incompatible existing state and require the operator to run the explicit full cleanup before retrying.

C) Other (describe after `[Answer]:`)

[Answer]: A

### Question 4 — Partial bootstrap failure

What should the lifecycle do if a required setup step fails, such as KDC initialization, metastore schema setup, bucket initialization, or permission provisioning?

A) Fail the dependent startup/ETL path at the failed step, report the failing component and preserve persistent state for inspection; do not continue as if authorization were ready (recommended; avoids misleading access results).

B) Start unrelated services in a degraded mode and let the operator decide whether to continue.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 5 — Cleanup behavior

How should the lifecycle handle the current `scripts/clean.sh` behavior, which runs `docker compose down -v` and removes named volumes?

A) Retain a full-reset command, clearly label that it destroys catalog/storage state and generated local state, and document a separate stop-only operation that preserves volumes (recommended; keeps reset capability explicit).

B) Change the standard cleanup command to preserve named volumes; provide a separate explicit full-reset command.

X) Other (describe after `[Answer]:`)

[Answer]: A

## Current Status

Functional Design artifacts are generated and checked against the approved requirements and Unit 1 scope. Storage-based authorization over RustFS remains a feasibility blocker until both Dremio and Spark effective-user outcomes are demonstrated; SQL-standard authorization remains outside the no-HiveServer2 baseline. Awaiting review and approval. No application configuration has been changed.
