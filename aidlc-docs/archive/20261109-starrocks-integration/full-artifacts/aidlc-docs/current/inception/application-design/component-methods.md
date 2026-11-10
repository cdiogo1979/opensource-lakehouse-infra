# Component Methods — StarRocks Integration

Signatures and purpose only. Business rules are defined in Functional Design.

## C2 Keycloak identities (`bootstrap-realm.py`)
- `starrocks_service_client_configuration(secret: str) -> dict`: the representation of the confidential `srv-starrocks` client (service account only, Polaris role mapper).
- `starrocks_login_client_configuration() -> dict`: the representation of the `starrocks` client (password grant, audience mapper).
- `ensure_service_account_group(api, client_uuid: str, group: dict) -> None`: makes the `srv-starrocks` service-account user a member of `role-default-writer`.

## C4 StarRocks bootstrap (`bootstrap-starrocks.py`)
- `class SqlRunner(Protocol)`: `query(sql: str) -> list[dict]` and `execute(sql: str) -> None`. SQL goes over stdin, and output is never echoed. Implementations: `DockerExecRunner(container)` and `NetworkRunner(host, port)`.
- `ensure_root_password(runner_factory, password_file: Path) -> str`: returns `"set"` or `"already-set"`.
- `ensure_backend(runner, host: str, heartbeat_port: int) -> str`: registers the BE if it is missing.
- `catalog_definition(env: Environment, credential_ref: str) -> dict[str, str]`: pure; the desired catalog properties, with the secret as a reference only.
- `plan_catalog(existing: dict[str, str] | None, desired: dict[str, str]) -> Literal["create", "equal", "conflict"]`: pure.
- `role_grants(matrix) -> list[Grant]`: pure; the grant statements for the five roles across catalogs and MV databases.
- `plan_grants(current: set[Grant], desired: set[Grant]) -> GrantPlan`: pure; the grants to add and the ones that are extra (reported, not revoked).
- `ensure_mv_databases(runner, names: list[str]) -> None`
- `main(argv) -> int`: CLI (`--dry-run`, and a skip notice when `STARROCKS_ENABLED=false`).

## C5 StarRocks user reconciler (`reconcile-starrocks-users.py`)
- `desired_users(memberships: dict[str, set[str]]) -> dict[str, set[str]]`: pure; Keycloak username to StarRocks roles, for users in at least one product group. Excludes `service-account-*` users, so `srv-starrocks` is never a SQL login (FR-7).
- `plan_users(current: dict[str, UserState], desired: dict[str, set[str]]) -> UserPlan`: pure; create, grant, revoke, set default roles, and remove.
- `jwt_identity_clause(username: str) -> str`: pure; the `IDENTIFIED WITH authentication_jwt AS '{...}'` JSON (JWKS URL, issuer, audience, principal field).
- `read_keycloak_memberships(api) -> dict[str, set[str]]`
- `read_starrocks_users(runner) -> dict[str, UserState]`: only users this reconciler manages (JWT users), never `root` or built-in users.
- `apply(runner, plan: UserPlan) -> None`
- `main(argv) -> int`: `--dry-run`, `--transport docker|network`.

## C7 Login helper (`starrocks-login.sh`)
- `starrocks-login.sh <username> [mysql args...]`: prompts for the password with no echo, gets the token, and runs the client container with the token file mounted read-only. The temporary file is removed on exit.

## C8 Lifecycle (`lakehouse.sh`)
- `starrocks_enabled() -> bool`: reads `STARROCKS_ENABLED` from `.env`; the default is `true`.
- `compose_files()`: the core file, plus `docker-compose.starrocks.yml` when StarRocks is enabled.
- New subcommand: `reconcile-starrocks [--dry-run]`.

## C8 Reset (`reset-lakehouse.py`)
- `VOLUMES` gains `lakehouse-local_starrocks-fe-meta` and `lakehouse-local_starrocks-be-storage`. `NETWORKS` gains `lakehouse-local_starrocks`.
