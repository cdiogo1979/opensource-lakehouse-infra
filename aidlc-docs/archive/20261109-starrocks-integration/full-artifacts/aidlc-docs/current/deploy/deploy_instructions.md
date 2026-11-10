# Deploy Instructions — StarRocks Integration

Target: a local `lakehouse-local` stack in a checkout of `opensource-lakehouse-infra-v2`. The development machine already runs this change. All steps are manual, run from the repository root, and need no reset.

## 1. Prerequisites
- **Action**: check resources and settings.
- **Prerequisites**:
  - Docker with Compose V2, Python 3, and OpenSSL.
  - At least 6 GB free for StarRocks: FE 2 GB and BE 4 GB by default, configurable in `.env`.
  - About 5 GB of disk for the images.
  - `.env` from `.env.example`. Add the `STARROCKS_*` keys if `.env` predates this change; enabled is the default.
- **Validation**: `docker info` shows enough memory.
- **Failure handling**: set `STARROCKS_ENABLED=false` to skip StarRocks entirely.

## 2. Start
- **Action**: `./scripts/lakehouse.sh start`. This creates the StarRocks credentials and TLS material, starts FE and BE, sets the root password, registers the BE, and reconciles the Keycloak `srv-starrocks` and `starrocks` clients.
- **Validation**:
  - `StarRocks is ready. SQL: 127.0.0.1:9030 ...`
  - `./scripts/lakehouse.sh status` shows `starrocks-fe` and `starrocks-be` healthy.
- **Failure handling**: rerun; it is idempotent. If the root password is refused, the FE metadata does not match `.runtime/credentials/starrocks-root-password`. Restore the file, or delete the two StarRocks volumes and start again.

## 3. Polaris grants and principal
- **Action**: `python3 infra/polaris/bootstrap-product-authorization.py`, then `python3 infra/polaris/reconcile-keycloak-groups.py`.
- **Validation**: the reconcile reports one more principal than before (`service-account-srv-starrocks`).
- **Failure handling**: rerun; both are idempotent.

## 4. StarRocks catalogs, roles, and users
- **Action**:
  - Run `./scripts/bootstrap-default-product.sh`.
  - **Blocker**: until the legacy Spark image issue is fixed, it stops at the Spark smoke step. If so, run the two StarRocks steps directly:
    ```sh
    python3 infra/starrocks/bootstrap-starrocks.py
    python3 infra/starrocks/reconcile-starrocks-users.py --transport docker
    ```
- **Validation**:
  - `StarRocks catalog ...: create` (or `equal`)
  - `StarRocks read <catalog>.<ns>.bootstrap_smoke_test: N row(s).` for all three catalogs
  - `StarRocks users reconciled: <n> desired; ...`
- **Failure handling**:
  - A catalog conflict names the catalog. Review it, then run `bootstrap-starrocks.py --recreate-catalogs`.
  - `LOAD_NAMESPACE_METADATA` forbidden means step 3 was skipped.

## 5. Scheduled sync
- **Action**: `docker compose -f docker-compose.yml -f docker-compose.starrocks.yml --profile scheduled-reconciliation up -d --build polaris-group-reconciler`. The product bootstrap does this too when it completes.
- **Validation**: its log shows `StarRocks user reconciliation succeeded` within one cycle (default 300 s).
- **Failure handling**: a `roles are not bootstrapped yet` message means step 4 has not run.

## 6. Validate logins
- **Action**: `./scripts/starrocks-login.sh joe-developer -e "SELECT CURRENT_USER(), CURRENT_ROLE()"`, and optionally the DBeaver setup in the README.
- **Validation**: `'joe-developer'@'%'` with `role_default_developer`.
- **Failure handling**: `insecure connection` means the FE was not recreated with TLS. Run `docker compose -f docker-compose.yml -f docker-compose.starrocks.yml up -d starrocks-fe`.

## Rollback
- Set `STARROCKS_ENABLED=false` and run `./scripts/lakehouse.sh stop` for the StarRocks services. Volumes are kept.
- Full removal: `./scripts/lakehouse.sh reset` removes all platform state, including StarRocks.
- The Polaris `NAMESPACE_READ_PROPERTIES` grant and the Keycloak clients remain until removed manually. No script exists for that.
