# Unit 1 Code Generation Plan — Polaris Database Path Layout

## Unit Context
- **Unit**: U1 — Default-product catalog and table path correction.
- **Purpose**: Keep Polaris catalog identifiers, namespaces, RustFS buckets, and Spark location verification consistent with the approved path layout.
- **Requirements**: FR-1 through FR-5 and NFR-1 through NFR-4 in `inception/requirements/requirements.md`.
- **Stories**: None; the approved workflow skips User Stories for this operator-facing infrastructure fix.
- **Dependencies**: Existing Keycloak, Polaris, RustFS, Docker Compose, and Spark runtime. No new service or library.
- **Interfaces**: Polaris management API, Iceberg REST catalog, RustFS S3 API, existing operator scripts.
- **Data entities**: Catalogs `lakehouse`, `lakehouse_uat`, `lakehouse_dev`; namespaces `default_lh`, `default_lhuat`, `default_lhdev`; smoke table `bootstrap_smoke_test`.
- **Expected resolved table locations**:
  - `s3://bucket-default/lakehouse/default_lh/bootstrap_smoke_test/`
  - `s3://bucket-default-uat/lakehouse_uat/default_lhuat/bootstrap_smoke_test/`
  - `s3://bucket-default-dev/lakehouse_dev/default_lhdev/bootstrap_smoke_test/`

## Generation Steps

1. [x] Update `infra/polaris/bootstrap-default-catalogs.py` to use the approved catalog names and set each default base location/allowed-location root to `<bucket>/<catalog>/`, leaving the namespace to contribute the database segment once. Preserve create-or-verify behavior and reject conflicting catalog storage configuration.
2. [x] Update `infra/polaris/bootstrap-product-authorization.py` to apply the existing role grants to `lakehouse`, `lakehouse_uat`, and `lakehouse_dev` without changing the approved role matrix.
3. [x] Update `infra/spark-bootstrap/create_smoke_tables.py` to use the renamed catalogs and check the complete resolved table root, including catalog, database, and table exactly once.
4. [x] Update `infra/spark-bootstrap/verify_role_matrix.py` to use the renamed catalogs and retained database namespaces; preserve current role/environment read-write expectations.
5. [x] Add an explicit one-time local reset operation in `infra/polaris/reset-default-product-once.py`. It requires a deliberate confirmation, is restricted to the three approved buckets and the known old/new default-product catalogs, removes object versions without deleting bucket resources, and is never called by routine `bootstrap-default-product.sh`.
6. [x] Update the operator procedure in `README.md` to document the one-time reset followed by normal bootstrap, while making clear that ordinary bootstrap reruns are non-destructive.
7. [x] Update `aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md` to reflect the approved catalog names and full path layout. Preserve unrelated historical knowledge files.
8. [x] Review the final diff for exact catalog/database/bucket mapping, destructive-scope guards, path assertions, and absence of secrets. The reset was not executed during code generation.

## Code Generation Boundaries
- Modify existing project files in place; do not create parallel or `_new` files.
- Create new application scripts only if existing RustFS/Polaris operator entry points cannot safely host the separately confirmed reset.
- Do not change Docker Compose topology, credentials, auth configuration, bucket names, database names, or role privileges.
- The one-time reset is not a deployment step and is not part of normal bootstrap.

## Completion Criteria
- All approved code-generation steps are complete and recorded.
- Existing bootstrap checks require the full expected table root and reject duplicate database segments.
- The explicit reset is isolated from normal bootstrap and constrained to the authorized resources.
- Generated changes are ready for Build and Test; no reset or runtime mutation occurs during code generation.
