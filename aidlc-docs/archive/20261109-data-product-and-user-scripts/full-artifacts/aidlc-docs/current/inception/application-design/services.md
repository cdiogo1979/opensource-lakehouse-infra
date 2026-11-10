# Services (Orchestration) — Data Product and User Scripts

## S1 Create and apply (`create-data-product.sh`)
**`--init <name>`**: validate the name, refuse if the file exists, and write `data-products/<name>.yaml` from the template. Nothing else changes.

**Apply `<file>`**, in order. Each step is a component script with `--product FILE`, and the first failure stops the run (rerun is safe).
1. **Validate** (C1): the schema, collisions with the other files, and locked names against the applied state.
2. **Keycloak** (C3): groups, client roles, platform-admin owner mapping, `srv-starrocks` writer membership, writer user and password file.
3. **RustFS** (C5): buckets, then group policies and the aggregated `role-platform-admin` policy.
4. **Polaris** (C6): allowed locations, namespaces in the product bucket, principal roles, namespace-scoped catalog roles.
5. **Polaris reconcile** (C8): current members get their principal roles now, not in five minutes.
6. **StarRocks** (C7), unless disabled: roles, database-scoped grants, MV databases, then the user reconcile.
7. **Jenkins** (C9): render the CasC file. If it changed and Jenkins is running, restart Jenkins (or print the command with `--no-restart`).
8. **Record** the applied state (C1) and print a summary: what was created, granted, or revoked, and any restart.

`--dry-run` runs step 1 and each component in dry-run mode, then prints the combined plan.

## S2 Remove (`remove-data-product.sh <name>`)
1. **Guard**: refuse `default`. Load the product file, falling back to the applied state when the file is missing.
2. **Inventory**: the Polaris tables, StarRocks MVs, and RustFS objects. If any exist and `--purge-data` is not given, stop and list the counts per environment. Nothing changes.
3. **Confirm**: the operator types the product name (or passes `--yes`).
4. **Back up** the file and the state to `.runtime/backups/<timestamp>-remove-<name>/`.
5. **Remove, in reverse dependency order**:
   1. Jenkins entries (render, then restart)
   2. StarRocks MV databases and roles
   3. Polaris tables (purge only), namespaces, catalog roles, principal roles, allowed locations
   4. RustFS objects (purge only), buckets, policies, then the platform-admin policy
   5. Keycloak writer user and password file, groups, client roles, and the platform-admin mapping
6. **Reconcile** Polaris and StarRocks, so former members lose their product roles.
7. **Delete** the product file and its state, and print a summary.

## S3 Create user (`create-user.sh`)
`create-user.py` with the given fields. Then a reminder: assign groups in the Keycloak admin console. Access follows within five minutes, or right away with `lakehouse.sh reconcile` and `reconcile-starrocks`.

## S4 Product bootstrap after a reset (`bootstrap-default-product.sh`)
- Realm and clients, bootstrap users, and the Polaris realm, as today.
- Then the S1 apply steps for **every** product file (`default.yaml` first), the smoke checks, and the scheduled reconciler.

## S5 Scheduled reconcile (`polaris-group-reconciler`)
Every cycle reads the mounted `data-products/*.yaml`. A product added or removed is covered on the next cycle with no image rebuild.

## One-time changes in this intent
- **Polaris**:
  - Add `ALLOW_NAMESPACE_CUSTOM_LOCATION` and the group pattern to `oidc.properties`.
  - Regenerate the runtime properties and restart Polaris once.
- **The `default` grant migration** (catalog-wide to namespace-scoped) runs in the first apply of `default.yaml`. Its order is set in Functional Design.
- **Jenkins**: it moves to the rendered CasC file (one restart). JupyterHub and Airflow get the read-only product mount (one recreate each).
