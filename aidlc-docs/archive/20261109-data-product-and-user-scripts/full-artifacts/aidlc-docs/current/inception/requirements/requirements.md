# Requirements — Data Product and User Scripts

## Intent Analysis
- **User request**: "next small intent , create two scripts , one to create a new data product - buckets, databases , roles , takes as parameter the data_product name and one to create a new user (role assignment can be done in keycloak)"
- **Type**: new operator capabilities.
- **Scope**: wide. The answers chose shared catalogs, all apps, and a writer per product, so the change reaches across all components, not only two scripts.
- **Complexity**: high. Grants change from catalog-wide to namespace-scoped, including for `default`.
- **Answers**: Q1 B, Q2 A, Q3 C, Q4 B, Q5 A, Q6 A, Q7 B, Q8 B, Q9 C, Q10 B; C1–C4 A.

## Product model (Q1 B, Q2 A, C1 A)
- **Name rule**: a product name is 2–20 characters of lowercase letters and digits, starting with a letter. `default` exists already; `lakehouse` and other reserved words are refused.
- **Environments**: each product has three, inside the **shared** Polaris catalogs:

  | Environment | Polaris catalog | Namespace | Bucket | Table path |
  |---|---|---|---|---|
  | prod | `lakehouse` | `<p>_lh` | `bucket-<p>` | `s3://bucket-<p>/lakehouse/<p>_lh/<table>` |
  | uat | `lakehouse_uat` | `<p>_lhuat` | `bucket-<p>-uat` | `s3://bucket-<p>-uat/lakehouse_uat/<p>_lhuat/<table>` |
  | dev | `lakehouse_dev` | `<p>_lhdev` | `bucket-<p>-dev` | `s3://bucket-<p>-dev/lakehouse_dev/<p>_lhdev/<table>` |

  `default` already follows this layout.
- **Groups**: `role-<p>-owner`, `role-<p>-developer`, `role-<p>-analyst`, `role-<p>-writer`.

## Functional Requirements

### FR-1 Product configuration files (Q5 A; changed by CR-1)
- Every product, `default` included, has one YAML file, `data-products/<name>.yaml`, holding its whole configuration:
  - name and description
  - per environment: catalog, namespace, bucket, MV database
  - the four group names
  - the access level per role and environment (`none`, `read`, `write`, `manage`), applied to Polaris, StarRocks, and RustFS, and the MV level (`none`, `read`, `author`, `manage`)
  - app mappings (JupyterHub admission, Airflow role, Jenkins permissions)
  - the writer user and its password file
- **Everything is editable (CR-Q1)**, within these rules:
  - **Group names** must match `role-<token>-(owner|developer|analyst|writer)` (CR-Q4).
  - **Catalogs** must be the shared environment catalogs (CR-Q5).
  - **Names never collide** with another product's.
- **Names are locked once applied (CR-Q6)**: a renamed bucket, namespace, group, or writer user is refused. To rename, remove the product and create it again. Access levels and app mappings can change at any time.
- Every bootstrap and reconciler reads these files, so a reset and rebuild recreate all products.

### FR-2 Create and apply script (Q6 A, C4 A; changed by CR-1)
- **`scripts/operations/create-data-product.sh --init <name>`** writes a standard `data-products/<name>.yaml` for review. It refuses if the file exists.
- **`scripts/operations/create-data-product.sh <file.yaml> [--dry-run] [--no-restart]`** validates the file and applies FR-3..FR-8. The script never prints secrets.
  - **Idempotent**: it creates what is missing, changes grants to match the file (including revokes after an edit), and refuses conflicts without changing them.
  - **`--dry-run`** prints the plan only.
  - **`default` is applied from `default.yaml` in the same way.**
- **Restarts**: only Jenkins, when its generated matrix changes. `--no-restart` prints the restart instead. Polaris restarts once in this intent, for the namespace-location flag and the filter pattern (AD-Q1, AD-Q2). JupyterHub and Airflow read the files at sign-in.

### FR-3 Keycloak (Q4 B)
- Groups `role-<p>-{owner,developer,analyst,writer}`, with Polaris client roles of the same names.
- `role-platform-admin` also carries `role-<p>-owner`.
- The `srv-starrocks` service account joins `role-<p>-writer`.
- The user `srv-<p>-writer` (default password `ChangeM3!`, permanent) is created in `role-<p>-writer`, with `.runtime/credentials/srv-<p>-writer-password`. It is ready for the product's future workloads; the Airflow broker is unchanged (C3 A).

### FR-4 Storage
- Buckets `bucket-<p>`, `bucket-<p>-uat`, `bucket-<p>-dev`.
- RustFS policies named after the product's groups, with the same access matrix as `default`. The `role-platform-admin` policy covers every product's buckets with owner rights.

### FR-5 Polaris (C1 A)
- Each shared catalog's allowed locations include the product's bucket.
- Namespaces are created with their location in the product bucket.
- Principal roles named after the product's groups are created.
- **Namespace-scoped grants, for every product including `default`**:
  - owner: everything in its namespaces, including drops
  - developer: read prod and UAT, write dev
  - analyst: read prod
  - writer: write all three
- Each role gets only the catalog-level read needed to list namespaces (`NAMESPACE_LIST`, AD-Q4). `role-platform-admin` is owner of every product through its `role-<p>-owner` client roles, as it is of `default` today.
- `default`'s catalog-wide grants are replaced by namespace-scoped ones; its tables and data are untouched.
- The OIDC principal-role filter is a fixed pattern accepting `role-<token>-(developer|analyst|owner|writer)` (AD-Q2).

### FR-6 StarRocks
- Roles `role_<p>_{owner,developer,analyst,writer}` with the same matrix on the product's databases in the three shared catalogs.
- MV databases `<p>_lh`, `<p>_lhuat`, `<p>_lhdev` in `default_catalog`.
- `role_platform_admin` covers every product.
- `default` moves to database-scoped grants in step with Polaris.
- **Developers author MVs in dev (CR-2)**: the MV level is read in prod and UAT, author in dev, for `default` and the template.
- The StarRocks user reconcile maps every product's groups.

### FR-7 Apps (Q3 C, C2 A)
Every product's groups get the same mapping as `default`:
- **JupyterHub**: admits developer and analyst groups.
- **Airflow**: owner Admin, developer and analyst User, writer Viewer.
- **Jenkins**: owner Administer, developer build, analyst read.

Owners of any product are therefore admins of the whole Airflow and Jenkins. This is documented.

### FR-8 Reconcilers
The Polaris group reconciler and the StarRocks user reconciler cover every registered product's groups. `srv-*` service users are handled as today.

### FR-9 Create-user script (Q7 B)
- **Command**: `scripts/operations/create-user.sh <username> [--email E] [--first-name F] [--last-name L] [--password-file F]`.
- **Behavior**: it creates an enabled Keycloak user in the `lakehouse` realm with the default password `ChangeM3!` (permanent), or with the password from a file. It assigns no groups; group assignment is done in Keycloak.
- **Existing users**: an existing username is refused without changes.
- **Next steps**: it prints a reminder that group changes reach Polaris and StarRocks within five minutes, or immediately with the reconcile commands.

### FR-11 Remove-data-product script (CR-1, CR-Q3)
- **Command**: `scripts/operations/remove-data-product.sh <name> [--purge-data] [--yes] [--dry-run] [--no-restart]`.
- **`default` is always refused.**
- **What it removes**:
  - Keycloak: the groups and their Polaris client roles, the client-role mapping on `role-platform-admin`, the `srv-starrocks` membership, and the writer user with its password file
  - RustFS: the buckets and policies, and the product's buckets in the `role-platform-admin` policy
  - Polaris: the namespaces, catalog roles, principal roles, and allowed locations
  - StarRocks: the roles and MV databases
  - Jenkins: the product's matrix entries
  - the YAML file and the applied-names state, after backing both up to `.runtime/backups/<timestamp>-remove-<name>/`
- **Data**: when any Iceberg table, MV, or bucket object exists, it stops and lists them. With `--purge-data` it drops the tables, deletes all bucket objects, and drops the MV databases.
- **Confirmation**: it always asks for the product name to be typed. `--yes` skips the prompt, for scripts.
- **Users**: they stay. Only their memberships go, and the reconcilers then remove their product access in Polaris and StarRocks.

### FR-10 README and tests
- README: "Data products" (configuration file, create, apply, remove) and "Adding users" sections, and the updated access model, including the platform-wide Airflow and Jenkins admin rights.
- Contract tests: file validation (patterns, collisions, locked names), the standard template, grant plans, app mappings, removal guards (`default`, data present).

## Non-Functional Requirements
- **Idempotency**: idempotent everywhere, with no secrets printed.
- **Verified live**:
  - create a product
  - check an owner, developer, and analyst of it
  - check `default` still works after the grant migration
  - check cross-product isolation (a `default` user cannot read the new product, and the reverse)
  - create a user
  - edit a product's access level and reapply
  - remove the product, first refused with data, then with `--purge-data`

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q8: B) |
| Property-Based Testing | No | Requirements Analysis (Q9: C) |
| Resiliency Baseline | No | Requirements Analysis (Q10: B) |

## Out of scope
- Per-product Airflow workloads (the broker for product writers).
- Product-scoped Airflow or Jenkins permissions.

## Change request CR-1 (2026-11-09, during Application Design)
> "also a script to remove the dataproduct (which cannot be the default) should be added , which removes all artifacts. in order to make it more modular , each data product , includoing the default should have a yaml file on all configurations are stored. the creation script to invoke that yaml file"

Changed: FR-1 (the registry becomes per-product YAML files) and FR-2 (`--init`, then apply a file). Added: FR-11 (removal). Product deletion moved into scope.

## Change request CR-2 (2026-11-09, during Code Generation)
> "developer role should be able to author starrocks mvs"

Clarified: dev only (read, read, author). This changes FR-6 and the standard template; `default` gains MV authoring in `default_lhdev` for developers.

## Change request CR-3 (2026-11-09, during Code Generation)
> "data-products folder should be at the root not inside infra folder"

The product files live in `data-products/` at the repository root.

## Change request CR-4 (2026-11-09, during Code Generation)
> "the scripts should take the platform-admin creadentials as parameters"

Clarified (AskUserQuestion): **Keycloak as admin + gate**, password from a file, `LAKEHOUSE_ADMIN_PASSWORD`, or a hidden prompt.
- `create-data-product.sh`, `remove-data-product.sh`, and `create-user.sh` take `--admin-user USER` (default `platform-admin`) and `--admin-password-file FILE`; without a file they use `LAKEHOUSE_ADMIN_PASSWORD`, then prompt without echo. A password is never a command-line value (argument abbreviations are disabled).
- Every Keycloak change signs in to the `lakehouse` realm as that user, and the scripts refuse unless the user is a member of `role-platform-admin`.
- Polaris, RustFS, and StarRocks steps, and the reconcilers, keep the protected bootstrap credentials in `.runtime/credentials/`; the realm bootstrap keeps the master admin.

## Assumptions confirmed in design (probes, 2026-11-09)
1. Allowed locations can be extended, and vending works for a namespace in another bucket. **A server-wide flag is required** (`ALLOW_NAMESPACE_CUSTOM_LOCATION`).
2. Namespace-level grants work. Listing namespaces shows every product's namespace names (accepted, AD-Q4).
3. StarRocks database-scoped grants on external catalogs: confirmed.
4. Jenkins CasC: rendered into `.runtime/container-mounts/`; Jenkins restarts after a change.
