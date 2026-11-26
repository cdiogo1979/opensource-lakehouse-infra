# Build and Test Summary — StarRocks Audit Capture

Intent `20261125-starrocks-audit-capture`, branch `starrocks-audit-capture`, 2026-11-26.

| Area | Result |
|---|---|
| Unit and contract tests | PASS: 729 host, 119 Airflow image, 13 broker; docs links OK; compose config OK |
| Images | PASS: both rebuilt with PyMySQL and `lakehouse_starrocks`; parity OK |
| Live capture (FE recreated) | PASS: AuditLoader 5.0.0 installed and idempotent; rows within a minute incl. logins; UTC; daily partitions |
| Security checks | PASS: loader INSERT-only; read grants only for the audit product's owner, developer and writer; no credential in the captured statements (StarRocks masks, the audit product redacts) |
| End to end (audit product, uat) | PASS: writer token login over TLS from a Spark run; bronze 704 rows; silver 728 events = 728 keys; five views refresh successfully |
| Jupyter password login | NOT RUN: needs the user's password |

## Findings
1. **Pre-existing**: the StarRocks bootstrap re-applies many existing grants on every run (also on `main`); the new table grants are recognised as current. Candidate follow-up.
2. **`start-airflow`'s final DAG check** loops while a product bundle has no DAGs (`audit-main` before its first promotion); Airflow itself is up. Candidate follow-up: accept empty bundles or warn instead of waiting.
3. **Stuck run cleaned**: a uat run from 2026-11-25 18:51 (before the platform pieces existed) had kept its Spark container for 13 hours after the DAG was paused; it ended when the DAG was resumed. Pausing a DAG with a failed, retrying task leaves its container until the run ends.
4. **Cross-intent**: AuditLoader writes `queryType` `disconnection` for logouts; the audit product now treats them as their own event type (merged into its `uat`, PR #2). No disconnection rows were observed yet on this stack.

## Extension compliance
- **Security Baseline (enabled)**: SECURITY-01 (TLS verified; plugin load on FE loopback, documented) compliant; -03 (no secrets in logs/reports, verified live) compliant; -06/-08 (least privilege, verified live) compliant; -10/-13 (vendored plugin with SHA-256; PyMySQL pinned) compliant; -11 (five misuse cases, two verified live) compliant; -12 (generated 0600 credentials, none in the repository) compliant; -02, -04, -05, -07, -09, -14, -15 N/A or unchanged (no new network-facing intermediary, web endpoint or API; existing hardening and monitoring apply).
- **PBT (Partial)**: PBT-02, -03, -07, -08, -09 compliant.
- **Resiliency**: disabled (N/A).

## Overall
Verification passed except the Jupyter password login, which needs the user.
