# Code Summary — metadata-grant

## Modified
- `infra/starrocks/bootstrap-starrocks.py`: `METADATA_DATABASE = "information_schema"`; `_catalog_grants` adds `SELECT ON ALL TABLES IN DATABASE information_schema` for every database-scoped product role with a level other than `none` (read, write, manage). The platform administrator's catalog-wide `ALL` is unchanged. Parsing, rendering and the revocation of uncovered grants already handle the form, so a catalog dropped to `none` revokes it.
- `tests/starrocks/test_starrocks_properties.py`: the P3 reference levels include the grant; new P9: for generated levels and database names per catalog, the grant is held exactly where `USAGE` is, only as `SELECT`, never on `DATABASE information_schema`.
- `tests/starrocks/test_product_access.py`: the own-databases check allows the metadata grant; new example test: render, parse round trip, `default`'s analyst (prod only) and developer (all three), revocation when access is removed.
- `README.md`: StarRocks section: "Browsing catalogs" for SQL clients (empty default database, `default_catalog`'s materialized-view databases, qualified names, filtered `information_schema`) and the role list.

## Local checks
- `python3 -m pytest -q tests`: 585 passed, 3 skipped; `tests/starrocks`: 47 passed.
- Flake8 on the changed files: one E302 in `test_starrocks_properties.py` line 18, present before this change (same in the archived copy). Bandit: B105 (the Keycloak token URL constant) and B608 (existing SQL rendering), both pre-existing; the change builds no SQL text.
