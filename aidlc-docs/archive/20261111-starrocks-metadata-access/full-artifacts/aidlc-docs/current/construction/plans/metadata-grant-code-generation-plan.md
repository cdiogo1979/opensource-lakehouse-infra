# Code Generation Plan — metadata-grant

The single source of truth for Code Generation of this unit. Workspace root: `/Users/carlosdiogo/code_repo/opensource-lakehouse-infra` (brownfield; files changed in place). Traceability: FR-1 to FR-5, NFR-1 to NFR-3.

## Steps
- [x] **Step 1 — Grant (FR-1, FR-2)**: `infra/starrocks/bootstrap-starrocks.py`, `_catalog_grants`: for a database-scoped product role with any level but `none`, also `Grant(role, "SELECT", catalog, "ALL TABLES IN DATABASE information_schema")` (constant `METADATA_DATABASE`). Catalog-wide scopes (the platform administrator's `ALL`) are unchanged. Parsing, rendering and revocation already handle the form.
- [x] **Step 2 — Tests (PBT partial)**: `tests/starrocks/test_starrocks_bootstrap_contract.py` (examples: `default`'s developer, analyst and owner get the grant exactly in their catalogs, an analyst none in uat or dev; the rendered statement; parsing `SHOW GRANTS` output round trip; a catalog dropped to `none` revokes it); `tests/starrocks/test_starrocks_properties.py` (property: for generated product matrices, a role holds the metadata grant on a catalog exactly when it holds `USAGE` there, and never any other privilege on `information_schema`).
- [x] **Step 3 — Docs (FR-4)**: README StarRocks section, "SQL clients (DBeaver)".
- [x] **Step 4 — Local checks**: `python3 -m pytest -q tests`, ruff, flake8 and bandit on the changed files; summary in `aidlc-docs/current/construction/metadata-grant/code/summary.md`.

## Not in this stage
Applying the bootstrap live, the temporary-user checks, and the canonical design update (closure).
