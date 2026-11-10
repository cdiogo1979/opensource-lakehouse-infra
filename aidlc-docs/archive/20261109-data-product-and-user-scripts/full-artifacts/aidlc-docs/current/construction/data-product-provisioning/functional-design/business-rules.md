# Business Rules — data-product-provisioning

## BR-1 File validation (before any change)
1. Every Domain Entities rule holds. On failure, nothing changes and the exit code is 2. The message names the file, field, and rule, never values from credential files.
2. **No collisions across product files**: no bucket, namespace, MV database, group, group token, or writer username is shared. A namespace and an MV database may share a name only within the same product, as today.
3. **Locked names**: if an AppliedState exists, the bucket, namespace, MV database, group, and writer username must equal it. Otherwise the run refuses with exit 2 and says to remove and recreate. A missing state (first apply, or after a reset) counts as unlocked.
4. **`default.yaml` reproduces today's model exactly**: the same names, the current access matrix, the MV matrix, and the app mappings. A contract test pins this.
5. **Unknown keys are refused**, so typos never pass silently.

## BR-2 Polaris privileges per level (namespace scope, FD-Q1 A)
**Catalog-level grants** on each role's catalog role, for every environment where the level is not `none`: `CATALOG_READ_PROPERTIES` and `NAMESPACE_LIST` (AD-Q4).

**Namespace-level grants** on the product namespace:

| Level | Privileges on the product namespace |
|---|---|
| read | `NAMESPACE_READ_PROPERTIES`, `TABLE_LIST`, `TABLE_READ_PROPERTIES`, `TABLE_READ_DATA`, `VIEW_LIST`, `VIEW_READ_PROPERTIES` |
| write | read, plus `TABLE_CREATE`, `TABLE_WRITE_PROPERTIES`, `TABLE_WRITE_DATA` |
| manage | write, plus `TABLE_DROP`, `TABLE_FULL_METADATA`, `VIEW_CREATE`, `VIEW_DROP`, `VIEW_FULL_METADATA` |

**Never granted to product roles**:
- `NAMESPACE_CREATE`, `NAMESPACE_DROP`, and `NAMESPACE_WRITE_PROPERTIES` (FD-Q1 A; a namespace's location never changes)
- `CATALOG_MANAGE_*`

Owners therefore lose `CATALOG_MANAGE_CONTENT` and `CATALOG_MANAGE_ACCESS`, which are catalog-wide today. Access changes go through Keycloak groups.

**Catalog roles**:
- A level of `none` means no catalog role for that role and catalog; an existing one is emptied and deleted. Today's empty `role-default-analyst-lakehouse_uat-catalog` and `…-lakehouse_dev-catalog` are deleted.
- A catalog role is bound to its principal role, as today.

## BR-3 StarRocks privileges per level (database scope)
| Level | Grants in catalog `c` for database `d` |
|---|---|
| read | `USAGE ON CATALOG c`, `SELECT ON ALL TABLES IN DATABASE d` |
| write | read, plus `INSERT ON ALL TABLES IN DATABASE d`, `CREATE TABLE ON DATABASE d` |
| manage | `USAGE ON CATALOG c`, `ALL ON DATABASE d`, `ALL ON ALL TABLES IN DATABASE d` |

- **No `CREATE DATABASE`** is granted to product roles (aligned with BR-2).
- **MV levels**: the same grants as today's MV matrix, on the product's MV database in `default_catalog`. **CR-2**: developers author MVs in dev (read, read, author), so `default`'s developers gain authoring in `default_lhdev`; this is the one deliberate increase.
- **`role_platform_admin`** keeps catalog-wide manage on the three catalogs, `ALL` on every product's MV database, and the built-ins.
- **Polaris is still the outer bound.** The shared catalog identity `srv-starrocks` has writer-level grants in every product, so drops through StarRocks stay refused. This is the existing, accepted limitation.
- **Coverage rule (unchanged)**: a privilege is covered when it is desired, or when `ALL` is desired on the same object.

## BR-4 RustFS policies
| Level | Bucket statement |
|---|---|
| none | no statement for that bucket |
| read | today's `read` actions |
| write | today's `read_write` actions |
| manage | `s3:*` on the bucket and its objects |

- **Product policies** (one per group) are product-owned and **converged**: rewritten when they differ. This replaces today's "verify, never overwrite", for the product groups only.
- **`role-platform-admin`** gets manage on every bucket of every product file, and is rewritten whenever the product set changes.

## BR-5 Keycloak
1. Groups, and Polaris client roles of the same name, are created if missing.
2. Each group carries its own client role. `role-platform-admin` carries every product's owner client role. Managed client roles of a removed product are removed from it.
3. The `srv-starrocks` service-account user is a member of every writer group.
4. **Writer user**: created if missing (enabled, email `<username>@lakehouse.local`, permanent password `ChangeM3!`, no required actions) and added to the writer group.
   - The password file is written only when the user is created, so an existing user's password is never reset.
   - `srv-default-writer` keeps its current source (`bootstrap-users.json` and `prepare-runtime.py`).
5. Existing users are never changed, apart from the writer user's group membership.

## BR-6 Apps
- **JupyterHub**: admits a user whose groups intersect the `apps.jupyterhub` groups of any product file, or `role-platform-admin`. The Hub admin is `role-platform-admin` only.
- **Airflow**: the role is the highest of the mapped roles (`Admin` > `User` > `Viewer`) across the user's groups and all files. `role-platform-admin` is `Admin`.
- **Jenkins**: the rendered matrix holds the static entries (`role-platform-admin`, `jenkins-break-glass`) plus each product role with permissions, in file and role order. The rendering is deterministic, so an unchanged set means no restart.
- **Unreadable files**: JupyterHub and Airflow fail closed (only `role-platform-admin` is admitted) and log the file name. The Jenkins render refuses, and the running Jenkins keeps its last good file.

## BR-7 Convergence (FD-Q3 A)
- **Additive first, then subtractive**, within one run: create objects, then add missing grants, and only then revoke. A role's access during a run is never less than the smaller of the old and new access.
- **Extra grants** on managed roles (product groups and `role_platform_admin`) that no file describes are revoked and reported by name. Unmanaged roles and principals are never touched.
- **The `default` migration** is BR-7 applied to `default.yaml`. The new namespace grants are added, then the old catalog-wide grants are revoked as extras. Build and Test checks with `role-matrix.py`, before and after, that each role's effective access is unchanged.
- **Deliberate reductions for `default`**, documented in the README and not counted as differences:
  - Polaris owners lose `CATALOG_MANAGE_CONTENT` and `CATALOG_MANAGE_ACCESS`.
  - Writers and dev developers lose catalog-wide `NAMESPACE_CREATE`.
  - StarRocks writers and owners lose `CREATE DATABASE` on the catalogs.

  `role-matrix.py` checks read and write per environment, which must not change.
- **`--dry-run`** prints the full add and revoke plan by object and privilege names, and changes nothing.

## BR-8 Removal
1. **`default` is refused** (exit 2), whatever the file says.
2. **Product source**: the file, or the AppliedState when the file is gone. If neither exists, the product is unknown (exit 2).
3. **Data inventory**: Polaris tables and views in the three namespaces, StarRocks tables and MVs in the three MV databases, and any object in the three buckets.
   - If anything exists and `--purge-data` is not given, it prints counts per environment and exits 1 with nothing changed.
4. **Confirmation**: the prompt lists the inventory counts and the groups' members (FD-Q2 A, excluding `srv-starrocks`). The operator must type the product name exactly; `--yes` skips this. Any other input exits 1 with nothing changed.
5. **Purge order**, all with the bootstrap identities:
   1. Drop Polaris views, then tables, without `purgeRequested`, since Polaris refuses purge.
   2. Delete every object version in the buckets.
   3. Drop the MV databases with `FORCE`.
6. **Idempotent and resumable**: a missing object counts as removed. The file and state are deleted last, after the backup, so a failed removal is rerun with the same command.
7. **Users stay.** The reconcilers then remove their product roles and drop StarRocks JWT users with no product group left (the existing rule).

## BR-9 Create user
- **Username**: `^[a-z0-9][a-z0-9._-]{1,62}$`. It must not start with `srv-` or `service-account-`, and must not be `admin` or `jenkins-break-glass`.
- **Existing username**: refused (exit 1), with no change.
- **Fields**: email defaults to `<username>@lakehouse.local`; first and last names are optional.
- **Account**: enabled, email verified, no required actions, no groups.
- **Password**: the first line of `--password-file`, or `ChangeM3!` when absent. It is permanent and is never printed or passed as an argument.

## BR-10 Safety and output
- **One run at a time**: a lock directory `.runtime/state/data-products/.lock` prevents concurrent apply and remove. A stale lock is reported with its age and is never removed automatically.
- **No secrets in output or arguments**: no passwords, secrets, tokens, or response bodies. Object and privilege names may be printed.
- **Exit codes**: 0 success; 1 operational failure or refusal at runtime; 2 usage or validation error.
- **StarRocks disabled** (`STARROCKS_ENABLED=false`): the StarRocks steps are skipped with a notice. The next apply with it enabled converges.
