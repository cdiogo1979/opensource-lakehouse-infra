# Business Logic Model — StarRocks Audit Capture

Rules: [business-rules.md](business-rules.md). Entities: [domain-entities.md](domain-entities.md).

## 1. `ensure_audit_capture(runner, credentials_dir, runtime_dir, dry_run)` (U1)
1. Run the staging DDL (AC-1); read `DESCRIBE starrocks_audit_db__.starrocks_audit_tbl__`; compute `column_problems` (AC-2) and report them.
2. Read or create the loader password (AC-3); look up `srv-auditloader` in `SHOW ALL AUTHENTICATION`; create or reset it and grant `INSERT` (AC-4).
3. Read the lock and verify the vendored package (AC-5).
4. Render `plugin.conf` (AC-6); build the package and its digest (AC-7); write it under `.runtime/starrocks-audit/` (atomic write: temporary file, then rename).
5. Read `SHOW PLUGINS` and the recorded digest; decide `install`, `reinstall` or `keep` (AC-8); execute; record the digest on success.
6. Return a report: table `created|exists|problems`, user `created|updated|conflict`, plugin `installed|reinstalled|kept|failed`, the plugin version. No secret in it.

`--dry-run` stops before every write and prints what it would do.

## 2. Grants (U2)
`data_products.parse_product` reads `platform_sources` (AC-13, AC-14). `starrocks_common.build_model` adds, per product and role with `read`, an audit scope; `bootstrap-starrocks.role_grants` turns it into the `TABLE` grant (AC-15); `parse_role_grants` recognizes `TABLE db.table`; `plan_grants` and `ensure_roles` do the rest unchanged.

## 3. `lakehouse_starrocks.connect()` (U3)
1. `connection_settings(os.environ)` (AC-17, AC-18).
2. Airflow: `current_writer_token` (AC-19); Jupyter: `getpass` (AC-20).
3. `pymysql.connect(...)` with verified TLS (AC-20).

## 4. Misuse cases and expected outcomes (SECURITY-11)
| Misuse | Outcome |
|---|---|
| A writer of another product (`srv-sales-writer`) runs `SELECT` on the staging table | Refused by StarRocks: no grant for `role_sales_writer` |
| An audit analyst queries the staging table or `audit_lh` tables | Refused: `analyst: none` in both `platform_sources` and `access.prod` |
| Someone edits the vendored zip in a branch | AC-5 checksum fails; nothing is installed; the reviewer sees the lock unchanged |
| The loader password leaks | Holder can only insert rows into the staging table; rotate with AC-3 |
| Workload code prints `connect()` arguments | No secret is held in an argument or attribute the module exposes; tokens stay inside PyMySQL |
| A run token leaks from a container | Bounded by the broker (run lifetime, revoked at `stop_cluster`); unchanged by this intent |

## 5. Failure behavior
| Situation | Behavior |
|---|---|
| Checksum mismatch | Audit capture step fails with a clear message; `start` reports it; StarRocks keeps running |
| `INSTALL PLUGIN` fails | Reported; digest not recorded, so the next start retries |
| Staging table has missing or retyped columns | Reported; plugin loads may fail; an admin fixes or drops the table |
| `srv-auditloader` exists with another login plugin | Reported as a conflict; not changed |
| Broker renewal fails | `connect()` raises; the task fails and retries |
| Wrong Jupyter password | StarRocks refuses; `connect()` raises PyMySQL's access-denied error (no password in it) |

## 6. Testable properties (PBT-01, partial)
| Function | Property | Category | Rule |
|---|---|---|---|
| `render_plugin_conf` | Parsing the rendered text gives the five set keys with their values and every other template key unchanged | Round-trip | PBT-02 |
| `build_package` | Unzipping gives the jar and properties byte-identical and the rendered `plugin.conf`; the same inputs give the same bytes | Round-trip, invariant | PBT-02, PBT-03 |
| `column_problems` | Empty for the expected list in any order and case; non-empty when a required column is removed or retyped | Invariant | PBT-03 |
| `plugin_action` | `keep` only when installed, `INSTALLED` and the digests match | Invariant | PBT-03 |
| `_platform_sources` | Accepts every combination of allowed levels; rejects any other role, source or level | Invariant | PBT-03 |
| `render_grant` / `parse_role_grants` | Rendering a `TABLE` grant and parsing StarRocks' `SHOW GRANTS` form of it gives the same grant | Round-trip | PBT-02 |
| `token_expires_soon` | For generated `exp` and `now`, true exactly when `exp - now <= margin` | Invariant | PBT-03 |
| `connection_settings` | Never returns without host, port in range, existing CA and user; never puts a secret in an error | Invariant | PBT-03 |

Generators (PBT-07): `plugin.conf` templates with comments and random extra keys; passwords from the generator's URL-safe alphabet; column lists from the entity table with random case and order; role names in the product pattern; JWTs with random `exp`. Seeds fixed and printed (PBT-08); Hypothesis (PBT-09).
