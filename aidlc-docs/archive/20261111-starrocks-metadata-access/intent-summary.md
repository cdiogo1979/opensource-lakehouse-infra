# Intent Summary: StarRocks Metadata Access

## Intent
StarRocks Metadata Access (`20261111-starrocks-metadata-access`)

## Objective
Let product users list Iceberg catalog tables in SQL clients (DBeaver) without error 5203, with no access beyond their roles.

## Date
2026-11-11

## Scope
Included: the information_schema metadata grant in bootstrap-starrocks.py, tests, README SQL-client guidance. Excluded: data privileges, the scheduled reconcile's bind-pattern timing (follow-up).

## Units / workstreams
metadata-grant

## Major requirements
- FR-1: every product role with USAGE on a catalog gets SELECT ON ALL TABLES IN DATABASE information_schema there.
- FR-2: converged and revoked with USAGE.
- FR-4: README guidance for SQL clients.
- NFR-2: no cross-product visibility.

## Architecture and design decisions
- StarRocks filters information_schema rows by the user's own privileges (probe 2), so the grant is safe in the shared catalogs.
- The grant joins the existing level model in _catalog_grants; platform admins unchanged.

## Implementation decisions
- METADATA_DATABASE constant; one Grant per database-scoped level other than none.
- P9 property; example test for render, parse, scope and revocation.

## Deviations
- Functional and Application Design skipped (rule fully stated in the requirements).

## Verification
construction/build-and-test/build-and-test-summary.md: pytest 585 passed, 3 skipped; live: 10 grants applied then converged; developer lists all three catalogs, analyst prod only; a metadata-only role sees nothing of default; the user confirmed DBeaver. Not run: a second real product.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/starrocks-sql-access.md

## Superseded decisions
- Product roles had no information_schema privilege; SQL-client table listings failed with error 5203.

## Archived artifacts
- aidlc-docs/archive/20261111-starrocks-metadata-access/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261111-starrocks-metadata-access/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261111-starrocks-metadata-access/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261111-starrocks-metadata-access/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/starrocks-sql-access.md
- aidlc-docs/archive/20261111-starrocks-metadata-access/full-artifacts/infra/starrocks/bootstrap-starrocks.py
- aidlc-docs/archive/20261111-starrocks-metadata-access/full-artifacts/tests/starrocks/test_starrocks_properties.py
- aidlc-docs/archive/20261111-starrocks-metadata-access/full-artifacts/tests/starrocks/test_product_access.py
- aidlc-docs/archive/20261111-starrocks-metadata-access/full-artifacts/README.md

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261111-starrocks-metadata-access/full-artifacts/`
