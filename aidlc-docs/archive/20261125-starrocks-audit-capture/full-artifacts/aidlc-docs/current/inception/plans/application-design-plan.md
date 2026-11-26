# Application Design Plan — StarRocks Audit Capture

Intent `20261125-starrocks-audit-capture`. Inputs: [requirements.md](../requirements/requirements.md), [execution-plan.md](execution-plan.md).

## Probe results (2026-11-25)
- **P-1 plugin source**: `StarRocks/fe-plugins-auditloader` has **no GitHub releases or tags**. The only official package is `https://releases.starrocks.io/resources/auditloader.zip`, an unversioned URL without a published checksum. Downloaded for inspection: 20344 bytes, `last-modified` 2025-08-28, SHA-256 `cd2a8aceb7943675192e80d7a6d02d675170ab3beba2d0d2f49b5bc8955a8ea2`; `plugin.properties`: `name=AuditLoader`, `version=5.0.0`, "Available for versions 3.3.11+", Java 11. Licensed Apache-2.0.
- **P-1 table**: the StarRocks 4.1 docs DDL (expression partition `date_trunc('day', timestamp)`, `partition_live_number`, `replication_num` 1, `DUPLICATE KEY (queryId, timestamp, queryType)`) with the columns queryId … warehouse; the README adds `ScanStats JSON NULL` for newer plugins. The 5.0.0 jar references: queryId, timestamp, queryType, clientIp, user, authorizedUser, resourceGroup, catalog, db, state, errorCode, queryTime, scanBytes, scanRows, returnRows, cpuCostNs, memCostBytes, stmtId, isQuery, feIp, stmt, digest, planCpuCosts, planMemCosts, pendingTimeMs, warehouse.
- **P-1 connection events**: recorded with `queryType` `connection` and `disconnection` when `fe.conf` has `audit_log_modules=slow_query,query,connection` (FE restart needed).
- **P-1 FE time zone**: the FE container runs in UTC (`/etc/localtime -> Etc/UTC`), so `timestamp` is UTC.
- **Cross-intent finding**: the audit product recognizes only `CONNECTION` as a connection marker; `disconnection` rows would be classified as queries. To fix in `opensource-lakehouse-audit-dp` (`CONNECTION_MARKERS`) before its dev validation.

## Plan
- [x] Answer the questions below (A, A; no ambiguity)
- [x] `components.md`, `component-methods.md`, `services.md`, `component-dependency.md`, `application-design.md`
- [x] Validate against FR-1 to FR-7, NFR-1 to NFR-4 and the Security Baseline

## Question 1
There is no versioned GitHub release. Where should the plugin package come from? (Supersedes requirements Q2:A, which assumed a pinned GitHub release.)

A) Vendor the official package in the repository: `infra/starrocks/plugins/auditloader-5.0.0.zip` (20 KB, Apache-2.0) with its SHA-256 and source URL recorded; verified before every install; no download at start, works offline; updating is a reviewed commit

B) Download `https://releases.starrocks.io/resources/auditloader.zip` at bootstrap into `.runtime/`, pinned by the SHA-256 above; if StarRocks replaces the file, the checksum fails and the bootstrap stops until someone reviews and updates the pin

C) Build from source at a pinned commit of `StarRocks/fe-plugins-auditloader` in a container at bootstrap

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
Recording logins needs `audit_log_modules=slow_query,query,connection` in `fe.conf` and an FE restart (StarRocks restarts briefly; password logins recover within a reconciler cycle, as after any restart). Include it?

A) Yes: add it to `infra/starrocks/conf/fe.conf`; it takes effect at the next StarRocks restart, which the deploy instructions schedule

B) No: queries only; the audit product's login view stays empty

C) Other (please describe after [Answer]: tag below)

[Answer]: A
