# Business Logic Model — starrocks-integration

## Runtime bootstrap (`bootstrap-starrocks.py --runtime-only`, run by core start)
1. If `STARROCKS_ENABLED=false`, print a notice and exit 0.
2. Wait for FE health (`/api/health`), up to `STARTUP_TIMEOUT_SECONDS`.
3. Apply the root password (SR-21).
4. Register the BE and wait until it is alive (SR-22).

## Product bootstrap (`bootstrap-starrocks.py`, run by `bootstrap-default-product.sh`)
1. Run the runtime steps (idempotent).
2. For each environment, build `catalog_definition(env)`. Read `SHOW CATALOGS` and `SHOW CREATE CATALOG`, call `plan_catalog` (SR-19), and apply. `--recreate-catalogs` applies SR-20.
3. Ensure the MV databases exist in `default_catalog`.
4. Ensure the roles exist. Compute `desired = role_grants(matrix)`, read the current grants of managed roles (`SHOW GRANTS FOR ROLE`), and compute `plan_grants(current, desired)`. Apply adds, then revokes (SR-10).
5. Smoke check: as root, using the catalog identity, `SELECT count(*)` from each `bootstrap_smoke_test`. The result is printed as a count only.

## User reconcile (`reconcile-starrocks-users.py`)
1. Opt-out check (SR-23).
2. Read the Keycloak memberships of the five groups (paged), giving username to groups. If the read fails or is empty, abort (SR-17).
3. `desired = desired_users(memberships)` (SR-13, SR-14).
4. Read the current managed users: JWT users only, with their roles and default roles (SR-16).
5. `plan = plan_users(current, desired)`. Apply in this order: create, grant, revoke, default roles, drop.
6. Print a summary of counts, plus the names of created and dropped users.

## Transports
`DockerExecRunner` runs `docker exec -i lakehouse-local-starrocks-fe-1 mysql -h127.0.0.1 -P9030 -uroot` with a client option file holding the password, created inside the container's private temp directory. `NetworkRunner` runs `mysql -h starrocks-fe -P9030 -uroot` (MariaDB or MySQL client) inside the reconciler container, with a mode-0600 option file. Both send SQL over stdin and parse tab-separated output.

## Testable Properties (PBT-01; partial mode enforces PBT-02, 03, 07, 08, 09)

| ID | Component | Category | Property |
|---|---|---|---|
| P1 | C4 `render_catalog_properties` / `parse_catalog_properties` | Round-trip (PBT-02) | Parsing the rendered `CREATE EXTERNAL CATALOG` property list returns the original mapping. Generators cover arbitrary safe keys and values, including quotes and special characters, escaped. |
| P2 | C5 `jwt_identity_clause` / `parse_jwt_identity` | Round-trip (PBT-02) | The JSON identity clause parses back to the same settings. |
| P3 | C4 `role_grants` | Invariant (PBT-03) | For every role and environment, the granted privileges are exactly the set for the matrix level. Analyst has no grant on uat or dev. No role has DROP on an external table unless its level is manage. |
| P4 | C4 `plan_grants` | Invariant (PBT-03) | After applying the plan, every desired grant is present and every managed-role grant is covered by the matrix, either desired or implied by `ALL` on the same object, because StarRocks may report `ALL` as individual privileges. Unmanaged-role grants are unchanged. (Corrected in Code Generation: equality was too strict.) |
| P5 | C5 `desired_users` | Invariant (PBT-03) | No `service-account-*` user and no user without a product group appear. Each user's roles equal the union of their groups' roles, plus the built-ins for platform admin. |
| P6 | C5 `plan_users` | Invariant (PBT-03) | Applying the plan to the current state yields the desired state for managed users. Non-JWT users are never dropped or changed. |
| P7 | C4 `plan_catalog` | Invariant (PBT-03) | `equal` exactly when the non-credential properties are equal. The credential never affects the outcome. |
| P8 | C4, C5 planners | Idempotence (advisory, PBT-04) | Planning against the desired state yields an empty plan. |

- **Generators (PBT-07)**: domain generators for usernames (including hyphens), group sets over the five groups plus unrelated groups, service-account names, grant sets, and catalog property maps.
- **Reproducibility (PBT-08)**: Hypothesis with its database and shrinking enabled, and seeds printed on failure (`print_blob=True`).
- **Framework (PBT-09)**: Hypothesis. It is already used in `tests/rustfs`, with its `tests/rustfs/strategies.py` pattern. StarRocks gets its own `tests/starrocks/starrocks_strategies.py`, because test module basenames must stay unique.
- **No PBT properties**: shell lifecycle wiring and the login helper. Those are covered by contract tests and the live Build and Test.
