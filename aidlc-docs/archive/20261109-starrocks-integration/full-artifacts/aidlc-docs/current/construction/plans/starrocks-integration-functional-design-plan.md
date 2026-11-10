# Functional Design Plan — starrocks-integration

## Plan
- [x] Answer the business-rule questions below
- [x] `domain-entities.md`: environments, catalogs, MV databases, roles, access levels, privileges, managed users, plans
- [x] `business-rules.md`: privilege mapping per level, role matrix, platform-admin rights, user sync, catalog conflicts, opt-out and skip, root password, failure behavior
- [x] `business-logic-model.md`: bootstrap and reconcile algorithms, transports, and testable properties (PBT-01)
- [x] Check consistency with FR-4..FR-7 and the Polaris matrix

## Baseline (Polaris, `infra/polaris/bootstrap-product-authorization.py`)
- **read**: `CATALOG_READ_PROPERTIES`, `NAMESPACE_LIST`, `TABLE_LIST`, `TABLE_READ_PROPERTIES`, `TABLE_READ_DATA`, `VIEW_LIST`, `VIEW_READ_PROPERTIES`
- **write**: read plus `NAMESPACE_CREATE`, `TABLE_CREATE`, `TABLE_WRITE_PROPERTIES`, `TABLE_WRITE_DATA` (no drop)
- **manage (owner)**: `CATALOG_MANAGE_CONTENT`, `CATALOG_MANAGE_ACCESS`

## Questions

## Question 1 — What "write" means in StarRocks
How should the StarRocks write level map to privileges on an external Iceberg catalog?

A) Mirror Polaris exactly. Write is read (`USAGE` on the catalog, `SELECT` on all tables) plus `CREATE DATABASE`, `CREATE TABLE`, and `INSERT`. No `DROP`, `DELETE`, or `ALTER` on tables. Manage is `ALL` (Recommended)

B) A broader write: also `DELETE`, `ALTER`, and `DROP` on tables in writable catalogs

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2 — Users who leave all product groups
What should the reconciler do with a StarRocks user whose Keycloak user is no longer in any product group, or no longer exists?

A) `DROP USER`. Their session ends at the next reconnect, and nothing is left behind (Recommended)

B) Revoke all managed roles but keep the user, so they can still log in with no data access

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3 — Extra privileges on the managed roles
If someone grants extra privileges to one of the five managed roles by hand, what should the bootstrap do?

A) Enforce the matrix exactly: revoke privileges on managed roles that the matrix does not include, and report what it revoked by name. Roles and users not managed by the bootstrap are never touched (Recommended)

B) Report extras only and never revoke, in the same style as the existing refuse-on-conflict bootstraps

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4 — Existing catalog with different settings
If a StarRocks catalog already exists with different non-secret settings, or when the `srv-starrocks` secret is rotated (StarRocks masks the stored secret, so it cannot be compared):

A) Refuse non-secret differences, naming the catalog only. Rotation and repair use an explicit `--recreate-catalogs` flag, which drops and recreates the three catalogs (no data loss: data lives in Polaris and RustFS) (Recommended)

B) Drop and recreate automatically on any difference

X) Other (please describe after [Answer]: tag below)

[Answer]: A
