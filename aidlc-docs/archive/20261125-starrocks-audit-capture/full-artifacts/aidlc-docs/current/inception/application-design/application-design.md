# Application Design — StarRocks Audit Capture (consolidated)

Intent `20261125-starrocks-audit-capture`. Details: [components.md](components.md), [component-methods.md](component-methods.md), [services.md](services.md), [component-dependency.md](component-dependency.md). Probes and decisions: [application-design-plan.md](../plans/application-design-plan.md).

## Decisions
| # | Decision | Source |
|---|---|---|
| AD-1 | Capture with AuditLoader 5.0.0 ("for 3.3.11+"), **vendored** at `infra/starrocks/plugins/auditloader-5.0.0.zip` with a lock file (version, source URL, SHA-256, Apache-2.0); verified before every install | AD-Q1:A (no GitHub releases exist) |
| AD-2 | Staging table from the StarRocks 4.1 docs DDL plus `ScanStats JSON NULL`; expression partition by day, `partition_live_number` 7, replication 1 | FR-1, P-1 |
| AD-3 | `fe.conf` `audit_log_modules=slow_query,query,connection`: connection and disconnection rows | AD-Q2:A |
| AD-4 | Loader user `srv-auditloader`, native password generated into `.runtime/credentials/` (0600), `INSERT` on the staging table only; `plugin.conf` with the plain password lives only in `.runtime/starrocks-audit/` (0600) and in the FE's plugin folder (AuditLoader's `secret_key` encryption is not used: its key would sit next to the password) | Q1:A, SECURITY-12 |
| AD-5 | Capture runs in `bootstrap-starrocks.py --runtime-only` on every start; the plugin is reinstalled only when the built package's digest changes | Q5:A, NFR-2 |
| AD-6 | `platform_sources.starrocks_audit` in product files drives `SELECT` grants through the existing grant planning (declared, kept, revoked) | Q3:A |
| AD-7 | `lakehouse_starrocks.connect()`: Airflow, writer token (renewed through `POST /v1/runs/token`) with the OIDC client handshake; Jupyter, the user's password with `getpass` on every call; TLS verified with the StarRocks CA | Q4:A, SECURITY-01 |
| AD-8 | PyMySQL added to the workload lock; images rebuilt | FR-5.5 |
| AD-9 | Run containers and Jupyter servers get the CA and `LAKEHOUSE_STARROCKS_*` variables | FR-6 |

## Units
- **U1 `starrocks-audit-capture`**: C1, C2, C3, `status`.
- **U2 `product-platform-sources`**: C4, C5, C6.
- **U3 `workload-starrocks-connection`**: C7, C8, C9, C10, images.

## Security design (Security Baseline)
- **Least privilege (SECURITY-06, -08)**: the loader can only insert into one table; readers get `SELECT` on one table only, through roles the product file declares; nothing else changes for other products.
- **Credentials (SECURITY-12)**: generated, 0600, never in the repository, logs, images or container environments; the Jupyter password is never stored.
- **Supply chain and integrity (SECURITY-10, -13)**: the plugin is vendored and SHA-256 verified; PyMySQL is pinned in the lock and covered by the existing scan workflow.
- **Transport (SECURITY-01)**: the helper uses TLS with certificate verification; the plugin's stream load goes from the FE to its own HTTP port on `127.0.0.1` inside the FE container (documented exception: no network hop).
- **Logging (SECURITY-03)**: reports and logs carry no token, password or `plugin.conf`.
- **Misuse cases (SECURITY-11)**:
  1. another product's writer queries the audit log: refused (no grant);
  2. an audit analyst reads full SQL: refused (`analyst: none`; FR-6.2 of the audit product);
  3. a tampered plugin package: the checksum check stops the install;
  4. a leaked loader password: it can only insert rows into the staging table (fake audit rows are the worst case; the audit product treats the table as raw input);
  5. a leaked run token: already bounded by the broker (run lifetime, revocation at the end of the run).

## Requirements traceability
| Requirement | Components |
|---|---|
| FR-1 | C1 (AD-2), C3 (AD-3) |
| FR-2 | C1 (AD-4) |
| FR-3 | C1, C2 (AD-1, AD-5) |
| FR-4 | C4, C5, C6 (AD-6) |
| FR-5 | C7, C8 (AD-7, AD-8) |
| FR-6 | C9, C10 (AD-9) |
| FR-7 | C6, docs |
| NFR-1 | security design above |
| NFR-2 | AD-5, grant planning |
| NFR-3 | optional block; unused variables harmless |
| NFR-4 | pure functions listed in component-methods |

## Cross-intent follow-up
The audit product (`opensource-lakehouse-audit-dp`) must treat `queryType = disconnection` as a connection event (`CONNECTION_MARKERS`), before its dev validation.
