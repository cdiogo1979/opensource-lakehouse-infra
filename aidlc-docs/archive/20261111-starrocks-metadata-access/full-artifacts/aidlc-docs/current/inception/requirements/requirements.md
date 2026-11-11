# Requirements — StarRocks Metadata Access

## Intent Analysis
- **Request**: "create the small intent to fix the starrocks permissions", after DBeaver showed "SELECT privilege(s) on TABLE tables" for `joe-developer` (`role_default_developer`) and a `default_lh` database near `lakehouse_dev`.
- **Type**: bug fix in the StarRocks access model (security-relevant). **Depth**: minimal to standard.
- **Evidence**: `inception/reverse-engineering/starrocks-metadata-access.md` (probes 1 and 2).

## Functional Requirements
- **FR-1 Metadata grant**: for every managed product role and every external catalog where the role has `USAGE` (any of read, write, manage), `infra/starrocks/bootstrap-starrocks.py` grants `SELECT ON ALL TABLES IN DATABASE information_schema` in that catalog (Q1 A). Platform admins already hold `ALL` on the catalogs and need nothing new.
- **FR-2 Convergence**: the grant is part of the desired privilege set, so the bootstrap adds it when missing, keeps it, and never reports it for manual review; removing a product's access to a catalog (level `none`) revokes it with `USAGE`.
- **FR-3 Behavior**: a product user can run SQL clients' table listings (`information_schema.tables`, `.columns`, `.views` in an external catalog) and sees exactly the databases and tables the user's grants already allow.
- **FR-4 Docs** (Q2 A): the README's StarRocks section gains "SQL clients (DBeaver)": connect with an empty default database (`default_catalog`), browse the Iceberg catalogs or use fully qualified names (`catalog.database.table`), and why `default_catalog` shows `default_lh`, `default_lhuat` and `default_lhdev` (the materialized-view databases).
- **FR-5 Canonical design**: `starrocks-sql-access.md` lists the new grant in the levels and the reason.

## Non-Functional Requirements
- **NFR-1 Least privilege**: no table, database or catalog privilege beyond the existing matrix; `information_schema` rows remain filtered by the user's privileges (probe 2).
- **NFR-2 No cross-product visibility**: a user of one product sees no table names of another product's databases in a shared catalog (verified with two products' worth of grants in Build and Test, or with temporary roles as in probe 2).
- **NFR-3 Idempotence**: repeated bootstrap runs change nothing after the first.

## Security Compliance (Requirements stage)
| Rule | Status | Note |
|---|---|---|
| SECURITY-06 Least privilege | Required | NFR-1 |
| SECURITY-08 Access control | Required | FR-1 to FR-3, NFR-2; StarRocks enforces, the verifier checks the misuse case |
| SECURITY-11 Secure design | Required | the grant lives in the existing grant model of the bootstrap |
| SECURITY-15 Fail closed | Required | without the grant listings are refused (today's behavior); no fallback |
| SECURITY-01, 02, 03, 04, 05, 07, 09, 10, 12, 13, 14 | N/A | no new data store, network path, endpoint, input surface, dependency, credential, or alerting |

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | Yes | Requirements Analysis (Q3: A) |
| Property-Based Testing | Partial (PBT-02, 03, 07, 08, 09 enforced) | Requirements Analysis (Q3: A) |
| Resiliency Baseline | No | Requirements Analysis (Q3: A) |
| Workflow Conventions | Yes (always enforced) | Workflow start |
