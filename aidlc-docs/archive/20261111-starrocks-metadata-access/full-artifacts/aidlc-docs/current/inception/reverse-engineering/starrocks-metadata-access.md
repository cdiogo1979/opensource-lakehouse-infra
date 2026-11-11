# Focused Reverse Engineering — StarRocks Metadata Access

## Symptom
DBeaver (MySQL driver) lists a database's tables with `SELECT ... FROM information_schema.tables t WHERE t.table_schema = '<db>'`, with an Iceberg catalog (`lakehouse`, `lakehouse_uat`, `lakehouse_dev`) as the current catalog. For product users StarRocks 4.1.7 refuses it: "you need (at least one of) the SELECT privilege(s) on TABLE tables". Audit log: refused for `joe-developer` in all three catalogs on 2026-11-11; no such queries earlier.

## Current design (canonical `starrocks-sql-access.md`)
- Product roles get `USAGE ON CATALOG c` and database-scoped table privileges (`SELECT ON ALL TABLES IN DATABASE d`, plus `INSERT` and `CREATE TABLE` for write, `ALL` for manage), applied by `infra/starrocks/bootstrap-starrocks.py`.
- No role has any privilege on an external catalog's `information_schema`.
- `default_catalog` holds the per-product materialized-view databases with the namespace names (`default_lh`, `default_lhuat`, `default_lhdev`); DBeaver shows them under the opened node, which is why `default_lh` appears near `lakehouse_dev` (that catalog holds only `default_lhdev`).

## Probe 1 (temporary native user with only `role_default_developer`, removed afterwards)
| Query (per catalog) | Developer user | Root |
|---|---|---|
| `SET CATALOG c;` then DBeaver's `information_schema.tables` query | refused (all three catalogs) | rows (all tables of the database) |
| `c.information_schema.tables` from `default_catalog` | refused | — |
| `SHOW TABLES FROM c.d` | OK (2, 16 and 2 tables) | — |
| `SELECT ... FROM c.d.bootstrap_smoke_test` | OK | — |
| `default_catalog` `information_schema.tables` | OK | — |

**Finding**: the grants are correct for data access; StarRocks checks `SELECT` on each external catalog's `information_schema` tables as objects of their own, which the product roles lack.

## Probe 2 (two temporary roles and native users on `lakehouse_uat`, removed afterwards; approved: "probe approved")
| Role | Grants | DBeaver listing of `default_lhuat` | Schemas visible in `information_schema.tables` |
|---|---|---|---|
| B, before the new grant | `USAGE` on the catalog, `SELECT ON ALL TABLES IN DATABASE default_lhuat` | refused (error 5203, the user's error) | — |
| A | `USAGE` on the catalog, `SELECT ON ALL TABLES IN DATABASE information_schema` only | 0 rows | `information_schema` only |
| B | as above plus `SELECT ON ALL TABLES IN DATABASE information_schema` | 17 rows (all of `default_lhuat`) | `default_lhuat`, `information_schema` |

**Findings**:
- StarRocks 4.1.7 accepts `SET CATALOG c; GRANT SELECT ON ALL TABLES IN DATABASE information_schema TO ROLE r`.
- `information_schema.tables` rows are filtered by the user's own privileges, so the grant reveals no table of a database the role can't access (no cross-product leak in the shared catalogs).
- Fix direction: give every managed role that has `USAGE` on an external catalog this grant on that catalog's `information_schema`; platform admins already hold `ALL` on the catalogs.

## Open question for the fix (answered by probe 2)
The external catalogs are shared by all products. Before granting `SELECT` on `c.information_schema`, the fix must show that `information_schema.tables` rows are filtered by the user's own table privileges; otherwise one product's users would see other products' table names. Probe 2 (two temporary roles: one with only the `information_schema` grant, one with the developer's grants plus it) answers this; it needs the user's approval because it creates roles and grants privileges.
