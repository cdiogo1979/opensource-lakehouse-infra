# PR request — StarRocks: let product roles read catalog metadata (SQL client table listings)

## Problem
SQL clients such as DBeaver list a database's tables with `information_schema.tables` in the Iceberg catalog. StarRocks 4.1.7 checks `SELECT` on each external catalog's `information_schema` tables, which no product role had, so product users got "SELECT privilege(s) on TABLE tables" (error 5203) in `lakehouse`, `lakehouse_uat` and `lakehouse_dev`, although `SHOW TABLES` and queries worked.

## Solution
`infra/starrocks/bootstrap-starrocks.py` grants every managed product role `SELECT ON ALL TABLES IN DATABASE information_schema` in each catalog where the role has `USAGE` (read, write, manage). StarRocks filters those rows by the user's own privileges, so a user sees only the databases and tables the role already grants (verified: a role with only this grant sees none of another product's tables). The grant converges and is revoked with `USAGE`, like the other grants.

## Main changes
- `infra/starrocks/bootstrap-starrocks.py`: `METADATA_DATABASE`; the grant in `_catalog_grants`.
- `tests/starrocks/`: P3 reference updated; new P9 property and an example test (render, parse, scope, revocation).
- `README.md`: StarRocks "Browsing catalogs" for SQL clients (empty default database, `default_catalog`'s materialized-view databases, qualified names).

## Verification
- `pytest`: 585 passed, 3 skipped.
- Live: 10 new grants applied, the next run converged; temporary developer and analyst users list tables exactly where their roles reach (analyst refused in uat and dev); a role with only the metadata grant sees nothing of `default`; the user confirmed DBeaver as `joe-developer`.
- Not run: a second real product (the cross-product case used a temporary role).

## Deployment
Two steps (apply the grants, then SQL-client users reconnect): [deploy_instructions.md](deploy_instructions.md).

## Risks and limitations
- Users must reconnect to pick up the grant (roles are read at login).
- The grant covers metadata only; data access is unchanged.
