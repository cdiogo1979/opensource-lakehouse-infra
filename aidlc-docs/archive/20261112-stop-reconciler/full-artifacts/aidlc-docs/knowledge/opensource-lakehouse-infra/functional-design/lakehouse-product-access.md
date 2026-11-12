# Functional Design — Lakehouse Product Access

Current functional design of the data product access model across Keycloak, Polaris, RustFS, and the apps, and of product provisioning and user creation. For architecture, see [`../application-design.md`](../application-design.md). History: the [RustFS Keycloak OIDC intent archive](../../../archive/20261030-rustfs-keycloak-oidc/intent-summary.md) (where this file was relocated from the retired `hive-dremio-rustfs` knowledge) the [Data Product and User Scripts intent archive](../../../archive/20261109-data-product-and-user-scripts/intent-summary.md), the [StarRocks LDAP Login intent archive](../../../archive/20261109-starrocks-ldap-login/intent-summary.md), and the [Data Product Airflow Bundles intent archive](../../../archive/20261109-data-product-airflow-bundles/intent-summary.md), and the [Spark S3 Checkpoints intent archive](../../../archive/20261111-spark-s3-checkpoints/intent-summary.md) (checkpoint keys).

## Data products
Each product is one file, `data-products/<name>.yaml`, validated by `infra/products/data_products.py`. `default` is the first product and cannot be removed.

| Field | Rule |
|---|---|
| `name` | `^[a-z][a-z0-9]{1,19}$`; not `lakehouse`, `platform`, `admin`, `srv`, `starrocks`, `polaris`; equals the file name |
| `environments.{prod,uat,dev}` | `catalog` must be the shared catalog (`lakehouse`, `lakehouse_uat`, `lakehouse_dev`). `namespace` and `mv_database` match `^[a-z][a-z0-9_]{1,63}$`. `bucket` is a valid S3 name; each environment has its own |
| `groups.{owner,developer,analyst,writer}` | `role-<token>-<role>`, one token per product |
| `access[role][env]` | `none`, `read`, `write`, `manage` (Polaris, StarRocks, RustFS) |
| `materialized_views[role][env]` | `none`, `read`, `author`, `manage` (StarRocks MV databases) |
| `apps` | `jupyterhub`: admitted roles; `airflow`: role → `Admin`, `User`, `Viewer`; `jenkins`: role (`developer`, `analyst`, `writer`; not `owner`) → folder permissions (no `Overall/*`) |
| `writer_user` | `srv-...` username; password file under `.runtime/credentials/` |
| `repo` (optional) | `url`: `https`, host and path, no user, password, port, query, or fragment, at most 300 characters; `prod_branch`, `uat_branch`: `^[A-Za-z0-9][A-Za-z0-9._/-]{0,99}$` without `..`, `//`, `@{`, or a trailing `/`, `.`, `.lock`. Gives the Airflow bundles `<name>-main` and `<name>-uat`. Several products may share a repository |

- **Across files**: no shared bucket, namespace, MV database, group token, or writer user. Unknown keys are refused.
- **Locked names**: buckets, namespaces, MV databases, groups, and the writer username are locked once applied (`.runtime/state/data-products/<name>.json`). Access levels and app mappings may change at any time.

## Product roles (`default`, as in `data-products/default.yaml`)

| Group / Polaris principal role | Production (`lakehouse`, `default_lh`) | UAT (`lakehouse_uat`, `default_lhuat`) | Dev (`lakehouse_dev`, `default_lhdev`) |
|---|---|---|---|
| `role-default-owner` | manage | manage | manage |
| `role-default-developer` | read | read | write |
| `role-default-analyst` | read | — | — |
| `role-default-writer` (service role) | write | write | write |

The template gives every new product the same matrix. Developers author MVs in dev (CR-2); see `starrocks-sql-access.md`.

## Polaris grants (`infra/polaris/bootstrap-product-authorization.py`)
- **Principal roles**: one per product group, with the same name.
- **Catalog roles**: per group and shared catalog where the level is not `none`, a catalog role `<group>-<catalog>-catalog`, bound to the principal role. It holds:
  - **catalog level**: `CATALOG_READ_PROPERTIES` and `NAMESPACE_LIST`. Every product's namespace names are therefore visible; contents are not.
  - **on the product's namespace only**:

    | Level | Namespace privileges |
    |---|---|
    | read | `NAMESPACE_READ_PROPERTIES`, `TABLE_LIST`, `TABLE_READ_PROPERTIES`, `TABLE_READ_DATA`, `VIEW_LIST`, `VIEW_READ_PROPERTIES` |
    | write | read + `TABLE_CREATE`, `TABLE_WRITE_PROPERTIES`, `TABLE_WRITE_DATA` |
    | manage | write + `TABLE_DROP`, `TABLE_FULL_METADATA`, `VIEW_CREATE`, `VIEW_DROP`, `VIEW_FULL_METADATA` |

- **Never granted to product roles**: `NAMESPACE_CREATE`, `NAMESPACE_DROP`, `NAMESPACE_WRITE_PROPERTIES`, and `CATALOG_MANAGE_*`. Each product has exactly its three namespaces.
- **Convergence**:
  - Missing grants are added first, then grants the files do not describe are revoked and reported.
  - A level of `none` empties, unbinds, and deletes the catalog role.
  - Unknown grant types and unmanaged roles are never touched.
  - `--dry-run` prints the plan.
- **2026-11-09 migration of `default`**: the catalog-wide grants were replaced by namespace-scoped ones; read and write per environment were unchanged. Deliberate reductions:
  - owners lost `CATALOG_MANAGE_CONTENT` and `CATALOG_MANAGE_ACCESS`
  - writers and dev developers lost catalog-wide `NAMESPACE_CREATE`
- **Catalogs and namespaces** (`infra/polaris/bootstrap-catalogs.py`): the shared catalogs keep the default product's base location and allow each product's `s3://<bucket>/<catalog>/`. Product namespaces carry the location `s3://<bucket>/<catalog>/<namespace>/`; an existing namespace elsewhere is a conflict.
- **OIDC filter**: Polaris accepts any `role-<token>-<role>` token role as a principal role; a role without grants grants nothing.

## Platform admin
`role-platform-admin` is owner of every product. It has no Polaris role of its own.
- Its Keycloak group carries every product's owner client role, and the reconciler gives its members every product's owner principal role.
- Its RustFS policy manages every product bucket.

| Service | `role-platform-admin` | A product's owner group |
|---|---|---|
| Polaris and RustFS | owner rights in every product | owner rights in that product |
| Airflow | `Admin` | per the product file (default `User`, platform-wide) |
| Jenkins | `Overall/Administer` | admin of the product's folder (all 22 folder permissions), plus `Overall/Read` |
| JupyterHub | admitted, and Hub admin | per `apps.jupyterhub` (default: not admitted) |
| Keycloak | `realm-admin` of the `lakehouse` realm (`realm-management` client); no `master` access | none |
| StarRocks | `role_platform_admin` (catalog-wide manage) plus built-in `user_admin`, `db_admin`, `cluster_admin` | its product role (database-scoped) |

## App access
- **JupyterHub**: admits the groups listed under each product's `apps.jupyterhub` (default: developer and analyst), plus `role-platform-admin`. The files are read at each sign-in through a read-only mount.
- **Airflow**: maps groups to roles from `apps.airflow` at each sign-in.
- **Airflow writes**: a run of a DAG from `<name>-main` or `<name>-uat` writes as that product's `writer_user`, and only if its DAG ID starts with that bundle name and Airflow confirms the bundle (`infra/airflow-token-broker/app.py`). No product can obtain another product's writer token through Airflow. `data_products.product_for_dag_id` and the broker share `DAG_ID_PATTERN`.
- **Jenkins**: one folder per product; the owner group is always its admin, and `apps.jenkins` grants the other roles permissions on that folder only. Product groups read Jenkins globally but see no other product's folder. With a `repo`, the folder holds `<name>_ci` and `<name>_cd` (see `jenkins-ci-access.md`).
- **Failing closed**: an unreadable or invalid product file admits only the platform administrator, in both JupyterHub and Airflow.

## User storage (LDAP, since 2026-11-09)
- **Where users and passwords live**: in the `ldap` directory, at `uid=<username>,ou=people,dc=lakehouse,dc=local` (`inetOrgPerson`). Keycloak reads and writes them through the writable provider `lakehouse-ldap` (`infra/keycloak/ldap_federation.py`).
  - **Provider settings**: `ldaps://ldap:636`, bind `cn=keycloak,ou=services,…`, `uid` as username and RDN, `entryUUID` as the Keycloak ID, users imported into Keycloak, registrations synced, passwords set through the password-modify operation (stored `{ARGON2}`).
  - **Mappers**: Keycloak's defaults (`cn` = first name, `sn` = last name, `mail`). Users without names are accepted.
- **Groups and local users**: groups and memberships stay in Keycloak; there is no LDAP group mapper. Client service accounts (`service-account-*`) and the `master` realm stay local.
- **One password everywhere**: the same username and password sign in to Keycloak (so every OIDC app) and to StarRocks. Every write through Keycloak goes to LDAP: admin-API user creation (`create-user.sh`, product writer users, bootstrap users), password resets (`bootstrap-users.sh`), and account-console changes.
- **Deleting a user**: deleting a federated user in Keycloak also deletes its LDAP entry.
- **Bootstrap**: `bootstrap-realm.py` ensures the provider (create, drift update, or conflict refusal) and Keycloak's bind test **before** any group or user, so fresh installs create users in LDAP.
- **Access control in LDAP**:
  - `cn=keycloak` writes `ou=people`.
  - Users may bind and change their own password; anonymous connections may only bind.
  - StarRocks binds as the user logging in.
  - The LDAP admin is for recovery only.
- **Migration of older stacks** (`scripts/operations/migrate-users-to-ldap.py`, once; `--dry-run`, `--yes`):
  - **Users**: local, non-service-account users with a valid `uid`. Disabled users are migrated as disabled.
  - **Passwords**: known values only — bootstrap users get `ChangeM3!`, writer users their password file, others `ChangeM3!` (reported by name). Keycloak's hashes cannot be exported.
  - **Per user**:
    1. write the entry and set its password
    2. verify the bind
    3. record the user's original state in `.runtime/state/ldap-migration.json`
    4. delete the local copy
    5. let Keycloak import the LDAP user (it gets a new ID)
    6. restore groups, names, email, and flags
    7. copy the Jupyter home to the new ID's volume; after file-count and byte verification, delete the old volume and the old Hub user (through the Hub's `lakehouse-maintenance` service, limited to `admin:users`)
  - **Safety**: the Keycloak database is dumped to `.runtime/backups/<time>-pre-ldap/` first; the local copy is deleted only after the bind is verified; a rerun finishes interrupted users first.
  - **Afterwards**: it removes the retired `starrocks` client and runs the Polaris and StarRocks syncs.

## Bootstrap identities (`infra/keycloak/bootstrap-users.json`)

| User | Group |
|---|---|
| `joe-developer` | `role-default-developer` |
| `peter-analyst` | `role-default-analyst` |
| `maria-owner` | `role-default-owner` |
| `srv-default-writer` | `role-default-writer` |
| `platform-admin` | `role-platform-admin` |

- **Password**: every user gets the documented local-development password `ChangeM3!`. It is permanent, with no required actions, and the email is `<user>@lakehouse.local`.
- **Create-only at start**: `infra/keycloak/bootstrap-realm.py` creates only missing users and never changes an existing user.
- **Enforce on demand**: `scripts/bootstrap/bootstrap-users.sh` (`infra/keycloak/bootstrap-users.py`) changes only the listed users. For each one it:
  - creates the user or updates the profile
  - resets the password, non-temporary
  - clears required actions
  - removes every other group
  - adds the default group

  It fails if the realm groups are missing. `scripts/bootstrap-default-product.sh` runs it after the realm bootstrap. Reconcile Polaris afterwards.
- **Writer credential**: `scripts/setup/prepare-runtime.py` writes the writer's password file from the same JSON. A changed `srv-default-writer` password breaks Airflow and Spark writes until `bootstrap-users.sh` restores it.
- **Writer client**: `lakehouse-writer` is confidential, password grant only, with no browser flow and no service account. Tokens last 3600 s and carry the Polaris role mapper. It accepts any realm user's credentials, but tokens carry only that user's roles.

## Provisioning and removal (operator commands)
- **Create or apply**: `scripts/operations/create-data-product.sh` (`--init <name>`, or apply `<file>` with `[--dry-run] [--no-restart]`).
  - Keycloak (`infra/keycloak/keycloak_products.py`): groups, Polaris client roles, the platform-admin owner mapping, and `srv-starrocks` in the writer group.
  - **Writer user**: created once, with the default password and its password file. The password is never reset. Bootstrap users (such as `srv-default-writer`) are left to `bootstrap-users.json`.
  - Then RustFS (buckets, policies, then checkpoint keys), Polaris, the Polaris sync, StarRocks, the StarRocks sync, Jenkins (folder, permissions, and jobs; restarted when changed), the applied state, and Airflow (recreated when its bundles or writers changed and it is running).
- **Remove**: `scripts/operations/remove-data-product.sh <name> [--purge-data] [--yes] [--dry-run]`.
  - It refuses `default`. It lists Polaris tables and views, StarRocks MV-database objects, and bucket object versions, and the members who lose access (FD-Q2). It stops while any data exists unless `--purge-data`.
  - It asks for the typed name (or `--yes`) and backs up the file and state.
  - **Removal order**:
    1. the Jenkins folder (with its jobs and build history) and global entries
    2. StarRocks MV databases (`FORCE`) and roles
    3. Polaris catalog and principal roles
    4. Polaris views and tables (dropped without purge; Polaris refuses purge), namespaces, and allowed locations
    5. RustFS checkpoint keys (users, policies, files), then object versions, buckets, and policies, then the platform-admin policy
    6. the Keycloak writer user and password file, groups, and client roles
    7. both syncs, then deleting the file and state
    8. Airflow (its bundles and writer go; recreated when running)
  - **Users stay.** Every step treats missing objects as removed, so a failed run resumes with the same command.
- **Create user**: `scripts/operations/create-user.sh <username> [--email] [--first-name] [--last-name] [--password-file]` (`infra/keycloak/create-user.py`).
  - **Username**: `^[a-z0-9][a-z0-9._-]{1,62}$`; not `srv-*`, `service-account-*`, `admin`, or `jenkins-break-glass`. An existing username is refused (exit 1).
  - **Account**: enabled and email-verified, no required actions, no groups. The password is `ChangeM3!` (permanent) or the first line of the file. The user and its password are stored in LDAP.
- **Credentials and safety**:
  - **Admin sign-in**: the three commands sign in to the `lakehouse` realm as a platform administrator. They take `--admin-user` (default `platform-admin`) and `--admin-password-file`, or `LAKEHOUSE_ADMIN_PASSWORD`, or a hidden prompt; argument abbreviations are off, so a password is never an argument. They refuse users without admin rights or outside `role-platform-admin`.
  - **Lock**: one operation runs at a time (`.runtime/state/data-products/.lock`).
  - **Output and exit codes**: no secrets are printed. Exit codes are 0 success, 1 runtime failure or refusal, 2 usage or validation.

## Authorization layers
1. **Identity**: Keycloak groups supply identity and role claims.
2. **Catalog**: Polaris maps product role claims to principal roles and namespace-scoped grants. Polaris-mediated Iceberg access vends scoped, short-lived RustFS credentials. Workloads (Spark through Airflow or JupyterHub) never receive root RustFS credentials, and table data is reached only through Polaris vending. The one bounded exception is **checkpoint keys**: static, non-root, limited to `checkpoints/` of one bucket (see "Checkpoint keys" below).
3. **Console**: RustFS console sessions carry the policies named by the user's `groups` claim. They govern direct object access in the console only.
4. **SQL engine**: StarRocks reaches Polaris as `srv-starrocks`, a member of every writer group.
   - StarRocks roles, named after the groups, narrow each SQL user to their product's databases.
   - Polaris is the outer bound: nothing beyond writer, so no table drops through StarRocks.
   - See `starrocks-sql-access.md`.

These layers are independent:
- Keycloak membership alone creates no Polaris grant; principals must be reconciled (`infra/polaris/reconcile-keycloak-groups.py`, every five minutes or on demand).
- Polaris grants do not grant RustFS console access, and RustFS console policies do not grant catalog operations.
- StarRocks roles are granted from Keycloak groups by `infra/starrocks/reconcile-starrocks-users.py`.

**Reconcilers**:
- Both read every product file and change nothing while a file is invalid.
- **Scheduled cycle** (`polaris-group-reconciler`, profile `scheduled-reconciliation`, every `POLARIS_GROUP_RECONCILE_INTERVAL_SECONDS`, default 300): the StarRocks bind-pattern step, the Polaris group sync, then the StarRocks user sync. The container runs the repository's current code (mounted read-only), so it can't fall behind the product model, and records each fully successful cycle; its healthcheck is unhealthy after two intervals plus a minute without one, shown by `lakehouse.sh status` (`reconciler`).
- A product group missing from Keycloak (a product being removed) counts as empty. Its roles are taken from everyone, the platform administrator included, and are no longer required in StarRocks.

## RustFS console policies (`infra/rustfs/bootstrap-policies.py`)

**Policy shape**
- Each product group, and `role-platform-admin`, has a RustFS IAM policy of exactly the same name.
- Every policy allows `s3:ListAllMyBuckets` on `arn:aws:s3:::*`, which reveals bucket names only.
- Every other resource is one of the product's bucket ARNs or their `/*` object ARNs.
- Statements are allow-only, and no policy contains an `admin:` action.

**Access levels**

| Level | Bucket actions | Object actions |
|---|---|---|
| read | `GetBucketLocation`, `ListBucket`, plus console metadata reads: `GetBucketPolicyStatus`, `GetBucketVersioning`, `GetBucketObjectLockConfiguration`, `GetBucketTagging`, `ListBucketVersions` | `GetObject`, `GetObjectTagging`, `GetObjectVersion`, `GetObjectRetention`, `GetObjectLegalHold` |
| read/write | read + `ListBucketMultipartUploads` | read + `PutObject`, `DeleteObject`, `AbortMultipartUpload`, `ListMultipartUploadParts` |
| manage | `s3:*` on the bucket and its objects | |

Product levels map as follows: `read` → read, `write` → read/write, `manage` → manage, and `none` adds no statement for that bucket.

**Rules**
- A user in several groups receives the union of their policies; effective access per bucket is the highest level among the user's groups.
- A user with no group value naming an existing policy is refused a console session by RustFS. Other group values are ignored.
- **Bootstrap**:
  - Product policies (and `role-platform-admin`) are owned by the product files and **converge**: missing ones are created, canonically equal ones accepted (order-insensitive comparison), and differing ones rewritten and verified.
  - A removal deletes the product's policies and rewrites the platform-admin policy.
  - The canonical comparison sorts `Action`, `Resource` and condition values (operator → key → values), because RustFS returns condition values in its own order.

## Checkpoint keys (`infra/rustfs/bootstrap-checkpoint-keys.py`)
Streaming checkpoint access, separate from the console policies and from Polaris vending (how Spark uses the keys: `workload-python-environment.md`).

**Entities** (one set per product environment bucket)
- Canned policy `checkpoints-<bucket>`: exactly two allow statements, `s3:ListBucket` on the bucket with `StringLike` `s3:prefix` in `checkpoints`, `checkpoints/*`, and `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject` on `<bucket>/checkpoints/*`. No wildcard bucket, no `ListAllMyBuckets`, no `admin:` action.
- RustFS user `ckpt-<bucket>`, enabled, with exactly that policy attached (not a service account: no root parent). Its secret is generated (`secrets.token_urlsafe(40)`) and never printed.
- Stored key `.runtime/credentials/checkpoint-keys/<bucket>` (folder 700, file 600) and staged copy `.runtime/container-mounts/checkpoint-keys/<bucket>` (folder 755, file 644; the parent `container-mounts` is 700), JSON `{"access_key", "secret_key"}`, written through a temporary file and renamed.
- `.buckets.json` in the staged folder: product → environment → bucket for the Airflow DAG factory; no secrets.

**Converge** (product bootstrap, `create-data-product.sh` after `bootstrap-policies.py`; idempotent)
- The policy converges like the group policies. A missing user is `created`; a user whose stored key is missing or no longer authenticates (a signed listing of `checkpoints/`) is re-keyed (`rotated`); otherwise `unchanged`. The secret changes in RustFS first; files change only after that succeeded. The policy attachment is set every run, and a missing or different staged copy is rewritten.
- A full run deletes staged files of buckets no longer in the product model. `--dry-run` writes nothing. `--check-staged` lists buckets without a staged key.

**Delivery by role**
- **Airflow**: each run container gets only its product environment's key: `prod` for `<product>-main`, `uat` for `<product>-uat` (`airflow-workflows.md`). Airflow never runs `dev`.
- **Jupyter**: at spawn (`check_current_admission`), `checkpoint_buckets` selects the `dev` bucket of every product where the user's current groups include the owner or developer group; `checkpoint_key_volumes` mounts each staged file read-only at `/run/secrets/lakehouse-checkpoints/<bucket>`, checked through the Hub's read-only folder mount `/run/secrets/checkpoint-keys` and the host path `JUPYTERHUB_CHECKPOINT_KEYS_HOST_DIR`. Never a `uat` or `prod` key; analysts, writers and the platform administrator get none. A missing or symlinked file for an eligible bucket fails the spawn naming the bucket. Membership changes apply at the next server start.
- A key belongs to a product environment, not to a person: code in a Jupyter server can read its dev keys, and a notebook and a dev stream with the same path share the checkpoint (accepted: dev is a sandbox).

**Rotation and removal**
- `./scripts/lakehouse.sh rotate-checkpoint-keys [--product FILE]` re-keys every selected bucket; the old secret is refused at once, so affected Airflow runs and Jupyter servers must restart.
- `remove-data-product.sh` removes the product's users, then policies, then files, before its buckets; absent items are not an error. `default` can't be removed.
- `scripts/lakehouse.sh start` warns and `start-airflow` refuses when a product bucket has no staged key; both create the staged folder first, so Docker never creates it. A full reset removes the keys with RustFS data and `.runtime/`.

## Failure behavior
- **Keycloak unavailable**: new token issuance, group reconciliation, and new RustFS OIDC logins fail. Already-issued tokens and console sessions remain usable until expiry. Root break-glass access to RustFS is unaffected.
- **LDAP unavailable**:
  - **Fails**: Keycloak sign-ins of federated users, user creation, password changes, and StarRocks password logins.
  - **Keeps working**: client-credentials service accounts, issued tokens, and open sessions.
  - **Syncs**: they read Keycloak's database and keep working.
- **Polaris principals**: Polaris needs a principal record for each Keycloak username before that user's data queries can be authorized. Reconcile after creating users or changing memberships.
- **Reconciler identity**: the reconciler and realm bootstrap currently use the protected local Keycloak bootstrap administrator. Replace it with a least-privilege identity before shared deployment.

## Verification
- **Spark S3 Checkpoints (2026-11-11)**: host tests (fake RustFS: converge, idempotence, rotation order and failure, removal order, file modes, pruning, no secret in output; Hypothesis P1 policy scope, P2 Jupyter selection never `uat`, `prod` or non-member products); live: three keys created, re-run `unchanged`; `scripts/verify/checkpoint-keys.py` 27/27 (own `checkpoints/` write 200, read 200, list 200, delete 204; other prefix, whole listing, bucket list and the other buckets 403); rotation refused the old secret at once; a `joe-developer` server mounted only `bucket-default-dev`. Only `default` exists, so the cross-product case used `default`'s other environment buckets.
- **Data Product Airflow Bundles (2026-11-09)**: writer selection per product verified live (`default`, and a test product sharing the repository); refusals for DAG IDs without a product, unknown DAGs, and a removed product; create and remove recreated Airflow, re-apply left it unchanged.
- **StarRocks LDAP Login (2026-11-09)**:
  - five users migrated with groups and profile kept, signing in to Keycloak with the same password; a Jupyter home copied
  - a password reset in Keycloak reaching LDAP and StarRocks at once
  - a new user and a product writer created in LDAP; deleting them removed their entries
- **Data Product and User Scripts (2026-11-09)**: the `default` migration left the role matrix identical. A second product was created, verified with isolation both ways, edited (an addition and a revocation), and removed. A new user's access followed group membership. App mappings were checked in the running containers.
- **StarRocks (2026-11-09)**: the read and write matrix through StarRocks matched the Polaris matrix for all five bootstrap users. The Polaris read set gained `NAMESPACE_READ_PROPERTIES` so StarRocks can load namespace metadata.
- **Environment reset (2026-10-31)**:
  - a rebuild from nothing; five bootstrap logins with one group each and the right Polaris role
  - `bootstrap-users.sh` restored the defaults after password, group, and required-action changes, and left a user outside the list alone
  - platform-admin got 200 on the `lakehouse` admin API and 403 on `master`; owner got 403
  - JupyterHub login confirmed by the user
- **Spark journey (U4)**: the Spark smoke-table journey and positive/negative read/write behavior verified for developer, analyst, owner, and writer in all environments.
- **Token handling (U2)**: wrong-audience and expired-token rejection, and Keycloak-outage behavior, verified. That intent closed under a waiver for the human PKCE callback and some reconciliation failure paths.
- **RustFS console (2026-10-30)**:
  - property-based tests over the policy definitions
  - a headless login and authorization run with temporary users: analyst read-only on production and denied elsewhere; developer writes dev only; console metadata reads allowed in scope and denied out of scope; refusal without a product group
  - a user-confirmed interactive developer login through a bucket view
- **Known limitation**: the RustFS 1.0.4 console bucket-list page loops for non-admin users (rustfs/console#271). Use `/rustfs/console/browser?bucket=<name>`.
