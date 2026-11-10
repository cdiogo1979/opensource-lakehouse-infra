# Build and Test Summary — StarRocks Integration

Run on 2026-11-09 against the live local stack. No reset was needed. **The result passed**, with three defects fixed during the run, two approved scope additions, one accepted limitation, and two earlier environment issues recorded.

## Results
| Check | Result |
|---|---|
| Static checks | Pass |
| Contract and PBT suite | 219 passed, 1 skipped, plus 2 earlier Airflow drift failures. StarRocks: 33 tests, including Hypothesis P1–P8. Broker tests: 10 passed |
| Runtime | FE and BE 4.1.7 healthy on arm64. Root password set once, then `already-set`. BE registered and alive |
| Keycloak | `srv-starrocks` and `starrocks` clients created. The service account is in the writer group. Polaris principal created by the existing reconciler (principals 5 to 6) |
| Catalogs | Created, then `equal` on rerun. Root read all three smoke tables (1 row each) through Polaris-vended RustFS credentials |
| Roles | 75 grants applied first time. A hand-added `DROP` on `role_default_writer` was revoked and reported |
| JWT login over TLS | Pass for all five bootstrap users, including hyphenated names. The certificate is verified (`VERIFY_IDENTITY`) and the default role is active |
| Access matrix | Reads and writes for all five users match the matrix exactly. Developer, analyst, and writer drops are denied by StarRocks; owner and platform-admin drops are denied by Polaris (see limitation) |
| MVs | Writer create, sync refresh, and scheduled async refreshes (`SUCCESS`, then `SKIPPED` when unchanged) pass. Developer read allowed; analyst read and developer refresh denied |
| Reconcile | Grant, create, revoke, and drop each followed Keycloak changes, ending with zero changes. Dry run changed nothing |
| JDBC (Connector/J 9.3.0) | Pass, as requested by the user. `idTokenFile` login as joe-developer (developer role, dev read) and peter-analyst (analyst role, dev denied). `sslMode=REQUIRED` and `VERIFY_IDENTITY` with a truststore both work. `starrocks-token.sh --watch` refresh works |
| Opt-out | Both scripts skip with a notice, and `status` omits StarRocks |
| Scheduled reconcile | Pass, after the role guard |
| Regression | RustFS OIDC 7/7, RustFS STS pass, Polaris negative cases pass, Polaris writer check pass. Role-matrix identity and Polaris parts 8/8. Jenkins 8/9 (the known missing CI job) |
| Resources | FE 808 MiB of 2 GiB, BE 445 MiB of 4 GiB |
| Cleanup | The probe MV and all 10 probe tables are dropped. Probe data files remain in the buckets, because Polaris refuses purge |

## Defects found and fixed during the run
1. **BE wait timed out**: 4.1.7 reports the backend host in `SHOW BACKENDS` column `IP`, not `Host`. Fixed with a fallback and a test.
2. **Polaris refused `LOAD_NAMESPACE_METADATA`**: StarRocks loads namespace metadata when it opens a database. Fixed by adding `NAMESPACE_READ_PROPERTIES` to the Polaris read set (approved by the user).
3. **Scheduled reconcile raced the product bootstrap**: it created users before the roles existed. Fixed: the reconciler changes nothing until the managed roles exist (SR-28).

## Scope additions approved during the run
- **SQL TLS** (SR-27): the MySQL OpenID Connect client plugin refuses to send a token in plaintext. Added a local CA and FE certificate, a PKCS12 keystore with a protected password, an FE entrypoint, and verified TLS in the login helper.
- **Polaris read set**: `NAMESPACE_READ_PROPERTIES` for all reading roles.

## Accepted limitation
- **Owner drops** (SR-29): owner and platform-admin cannot drop Iceberg tables through StarRocks. Polaris refuses `TABLE_DROP` for the writer-level `srv-starrocks`. Owners drop through Spark or Polaris. This is documented in the README.

## Earlier environment issues (not caused by this intent)
- The legacy image `local/spark-iceberg:3.5.5_1.8.1-krb5` is no longer present.
  - `scripts/run-bootstrap-smoke-spark.sh` and the Spark data part of `verify-role-matrix.py` cannot run.
  - So `bootstrap-default-product.sh` stops at the Spark smoke step, before its two StarRocks steps, which were run directly here.
  - The v2 runtime image is not a drop-in replacement.
  - Follow-up: move both scripts to the v2 Spark runtime.
- The Jenkins CI job is still missing after the earlier reset.

## Follow-up requested during Build and Test
- BI and Power BI access becomes a new intent after this one: long-lived per-data-product Keycloak tokens, with roles from Keycloak groups and Power BI through ODBC (to verify). The token lifetime is decided there. See `aidlc-state.md`, Open Follow-ups.
