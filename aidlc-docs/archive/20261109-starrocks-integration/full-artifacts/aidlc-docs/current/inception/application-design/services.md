# Services and Orchestration — StarRocks Integration

## S1 Core start (`lakehouse.sh start`)
1. Prepare credentials, including the StarRocks root password and the `srv-starrocks` secret.
2. Start the providers, run the realm bootstrap (which now includes `srv-starrocks` and `starrocks`), then JupyterHub and Jenkins.
3. If StarRocks is enabled: `docker compose -f docker-compose.yml -f docker-compose.starrocks.yml up -d starrocks-fe starrocks-be`, then wait for health.
4. Then run `bootstrap-starrocks.py --runtime-only`, which sets the root password and registers the BE.

The core start creates no catalogs, roles, or users. Those are product resources, which matches the existing rule that start does not apply product changes.

## S2 Product bootstrap (`bootstrap-default-product.sh`)
After the Polaris catalogs, grants, and Polaris reconcile:
1. `bootstrap-starrocks.py`: catalogs, roles and grants, MV databases.
2. `reconcile-starrocks-users.py --transport docker`.
3. A StarRocks smoke check: as `srv-starrocks`, through the catalog, read the three `bootstrap_smoke_test` tables.

When StarRocks is disabled, these steps print a notice and are skipped.

## S3 User reconcile
- **On demand**: `lakehouse.sh reconcile-starrocks [--dry-run]` uses the `docker exec` transport.
- **Scheduled**: each `polaris-group-reconciler` cycle runs the Polaris reconcile, then `reconcile-starrocks-users.py --transport network` against `starrocks-fe:9030` on the `core` network. If StarRocks is disabled or unreachable, it logs one notice and continues.

## S4 User login
`starrocks-login.sh joe-developer`:
1. Get a password-grant token from the `starrocks` client.
2. Write the token file (mode 0600, temporary).
3. `docker run --rm -it --network lakehouse-local_core mysql:<9.x pinned> mysql -h starrocks-fe -P 9030 -u joe-developer --plugin-dir ... --authentication-openid-connect-client-id-token-file=/run/token`

## S5 Query path
1. The StarRocks FE checks the user's role grants.
2. The `lakehouse_dev` catalog calls Polaris as `srv-starrocks`, with an OAuth2 token that is renewed automatically.
3. Polaris returns table metadata and vended RustFS credentials.
4. The BE reads the files from `rustfs:9000`.

## S6 Reset
`reset-lakehouse.py` removes the StarRocks containers (Compose project label), the two volumes, and the `starrocks` network, along with everything else.
