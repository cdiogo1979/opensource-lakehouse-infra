# Requirements: Correct Polaris Table Object Paths

## Intent Analysis
- **User request**: Correct the default-product Iceberg table layout and catalog names. The requested path is `<bucket>/<catalog>/<database>/<table>`.
- **Request type**: Bug fix with catalog and storage-layout adjustment.
- **Scope estimate**: Single infrastructure component plus smoke-table verification and operator documentation.
- **Complexity estimate**: Simple; the catalog base location and namespace are currently both adding the database segment, and the location assertion is too permissive.

## Functional Requirements

### FR-1: Catalog names
Use these Polaris catalog names:
- Production: `lakehouse`
- UAT: `lakehouse_uat`
- Development: `lakehouse_dev`

### FR-2: Database/namespace names
Retain the existing environment-specific database namespaces:
- Production: `default_lh`
- UAT: `default_lhuat`
- Development: `default_lhdev`

### FR-3: Table object layout
Tables created in each environment must have object paths in the form `<bucket>/<catalog>/<database>/<table>`, with exactly one occurrence of each segment. For example, production tables use `bucket-default/lakehouse/default_lh/<table>`.

Use the existing environment bucket mapping:
- Production: `bucket-default`
- UAT: `bucket-default-uat`
- Development: `bucket-default-dev`

The catalog default base location and namespace location must combine to produce that path without repeating the namespace/database name.

### FR-4: Fresh local storage state
For the initial application of this fix, empty all objects from the three configured buckets and recreate the Polaris catalogs, namespaces, and smoke tables using the new paths. This is a one-time reset authorized for the current local environment. Do not make routine bootstrap reruns empty buckets or delete existing tables/data.

### FR-5: Bootstrap and smoke verification
The normal bootstrap remains idempotent and non-destructive. Smoke-table verification must assert the complete expected path, including the catalog segment and a single database segment; a broad prefix check is insufficient.

## Non-Functional Requirements

- **NFR-1: Data safety**: Keep bucket clearing as an explicit one-time operation. The regular bootstrap path must preserve objects and existing tables.
- **NFR-2: Access boundaries**: Preserve the current environment-specific catalog, bucket, and vended-credential access boundaries.
- **NFR-3: Secret handling**: Do not expose or log credentials while changing or verifying the bootstrap.
- **NFR-4: Maintainability**: Keep the environment-to-catalog/database/bucket mapping defined consistently and make the full path expectation visible in verification output or diagnostics.

## Technical Context

The current catalog bootstrap uses `s3://<bucket>/<database>/` as the catalog default base location and creates the same database name as a namespace. Spark then creates tables within that namespace, yielding a duplicated namespace segment. The existing smoke check only checks that the location starts with the bucket/database prefix and does not validate the catalog segment or reject duplication.

## Extension Decisions

| Extension | Decision | Scope |
|---|---|---|
| Security Baseline | No | Not enabled for this intent |
| Property-Based Testing | No | Not enabled for this intent |
| Resiliency Baseline | No | Not enabled for this intent |

## Acceptance Criteria

1. Polaris catalogs are named `lakehouse`, `lakehouse_uat`, and `lakehouse_dev`.
2. Their namespaces remain `default_lh`, `default_lhuat`, and `default_lhdev`, respectively.
3. Each smoke table's resolved location matches `<bucket>/<catalog>/<database>/<table>` and contains the database name exactly once.
4. The one-time local reset empties the three configured buckets before recreating the catalog objects and smoke tables.
5. A subsequent normal bootstrap rerun preserves bucket objects and does not duplicate smoke-table rows.
6. No credentials appear in logs or generated artifacts.
