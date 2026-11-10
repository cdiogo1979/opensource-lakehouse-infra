# PR Request — StarRocks integration

_Proposed PR description. No pull request has been created; this workspace has no git metadata._

## Problem
The platform had no interactive SQL engine. The StarRocks assets in the repository belonged to the retired Kerberos, FreeIPA, and Hive stack and could not run in v2. The product bootstrap had no step for a SQL engine's catalogs, and nothing aligned engine roles with the product roles.

## Solution
- **Runtime**: StarRocks 4.1.7 (one FE, one BE, upstream images pinned by digest, arm64) runs from its own `docker-compose.starrocks.yml` in the `lakehouse-local` project. It is part of the core `start`, `status`, and `stop`, with an opt-out `STARROCKS_ENABLED=false`. Ports bind to loopback, and FE and BE memory limits are configurable.
- **Catalogs**: the product bootstrap creates three Iceberg REST catalogs on Polaris (`lakehouse`, `lakehouse_uat`, `lakehouse_dev`).
  - They authenticate as the Keycloak service account `srv-starrocks` (writer group) with OAuth2 client credentials, renewed by StarRocks.
  - Data access uses Polaris-vended RustFS credentials; StarRocks holds no storage keys.
  - The bootstrap also creates three internal materialized-view databases.
- **Roles**: five StarRocks roles named after the Keycloak groups, with the same matrix as Polaris.
  - The bootstrap enforces them: privileges the matrix does not cover are revoked and reported.
  - Platform admins also get StarRocks system administration.
- **Users**: every Keycloak user in a product group gets a StarRocks user that logs in with a Keycloak access token (audience `starrocks`) and holds exactly their groups' roles.
  - A reconciler keeps them in sync. It runs in the bootstrap, on demand (`lakehouse.sh reconcile-starrocks`), and on the existing schedule.
  - It never touches root or password users, and changes nothing if Keycloak is unreadable or the roles are missing.
- **Login**:
  - `scripts/starrocks-login.sh` uses a MySQL 9.7 client with its OpenID Connect plugin, over TLS verified against a local StarRocks CA.
  - `scripts/starrocks-token.sh` keeps a token file fresh for JDBC clients such as DBeaver (Connector/J 9.1+ `idTokenFile`).
- **Legacy**: the Kerberos, LDAP, and Hive StarRocks assets were retired. They are kept in the intent archive.

## Main changes
| Area | Paths |
|---|---|
| Runtime | `docker-compose.starrocks.yml` (new), `infra/starrocks/conf/{fe,be}.conf` (new), `infra/starrocks/fe-entrypoint.sh` (new), `.env.example`, `docker-compose.deferred.yml` |
| Bootstrap and sync | `infra/starrocks/starrocks_common.py`, `bootstrap-starrocks.py`, `reconcile-starrocks-users.py` (all new) |
| Identity | `infra/keycloak/bootstrap-realm.py`, `infra/keycloak/realm-contract.json` (`srv-starrocks` and `starrocks` clients) |
| Polaris | `infra/polaris/bootstrap-product-authorization.py`: the read set gains `NAMESPACE_READ_PROPERTIES` |
| Scheduled sync | `infra/polaris/reconciler/{Dockerfile,run.sh}`, and the `polaris-group-reconciler` service in `docker-compose.yml` |
| Lifecycle | `scripts/lakehouse.sh`, `scripts/bootstrap-default-product.sh`, `scripts/reset-lakehouse.py`, `scripts/prepare-lakehouse-runtime.py`, `scripts/prepare-starrocks-certificates.py` (new) |
| Clients | `scripts/starrocks-login.sh`, `scripts/starrocks-token.sh` (new) |
| Retired | `infra/starrocks/{fe,be,kerberos,ldap-access,sql-bootstrap,preflight}`, `infra/starrocks/conf/{core-site,hive-site}.xml`, `scripts/bootstrap-starrocks-sql.sh` |
| Docs and tests | `README.md` ("StarRocks SQL", "DBeaver and other JDBC clients", "Keycloak sign-in"); `tests/starrocks/` (new: 33 tests including Hypothesis P1–P8); updated Keycloak and reset tests |

## Verification
Build and Test passed on 2026-11-09 against the live local stack. See `aidlc-docs/current/construction/build-and-test/build-and-test-summary.md`.
- **Tests**: 219 passed, 1 skipped, plus 2 earlier Airflow drift failures (unchanged, out of scope).
- **Live**: runtime and idempotent reruns; catalogs and smoke reads through vended credentials; grant enforcement; token login over verified TLS for all five bootstrap users; the full read/write access matrix; MV create, sync refresh, and scheduled refresh; reconcile drift in both directions; opt-out; scheduled sync; JDBC with Connector/J 9.3.0; memory fit.
- **Regression**: RustFS OIDC and STS, Polaris checks, and the role-matrix identity and Polaris parts pass. Jenkins passes 8 of 9 (the known missing CI job).
- **Not run**: performance and load. Power BI was not tested; it is a planned follow-up intent.

## Deployment
Ordered steps are required. See [deploy_instructions.md](deploy_instructions.md).

## Risks and limitations
1. **No owner drops through StarRocks**: owner and platform-admin cannot drop Iceberg tables there. Polaris refuses `TABLE_DROP` for the writer-level `srv-starrocks`. Accepted; owners drop through Spark or Polaris.
2. **Shared catalog identity**: `srv-starrocks` is writer-level on all three catalogs. Per-user limits come from StarRocks roles, not Polaris.
3. **Polaris read change**: `NAMESPACE_READ_PROPERTIES` is now granted to every reading role (read-only metadata).
4. **TLS**: only token logins are forced onto TLS. Password logins such as `root` are not (`ssl_force_secure_transport=false`). The CA is local and is regenerated by a reset.
5. **Short tokens**: user tokens last 5 minutes. Interactive clients need `starrocks-token.sh --watch`. Power BI and other scheduled tools are not supported yet.
6. **MV authors**: a dropped user's materialized views may stop refreshing.
7. **Earlier environment issue**: the legacy Spark image `local/spark-iceberg:3.5.5_1.8.1-krb5` is missing.
   - `run-bootstrap-smoke-spark.sh` fails, and `bootstrap-default-product.sh` stops before its StarRocks steps.
   - Those steps must be run directly until both scripts move to the v2 Spark runtime.
8. **Probe residue**: data files from the Build and Test probe tables remain in the buckets, because Polaris refuses purge. Their metadata was dropped.
