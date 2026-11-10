# Domain Entities — data-product-provisioning

## Product (from `data-products/<name>.yaml`)
| Field | Type | Rule |
|---|---|---|
| `apiVersion` | string | `lakehouse.local/v1` |
| `name` | string | `^[a-z][a-z0-9]{1,19}$`, not reserved (`lakehouse`, `platform`, `admin`, `srv`, `starrocks`, `polaris`); equals the file name |
| `description` | string | 1 to 200 printable characters |
| `environments` | map of exactly `prod`, `uat`, `dev` → Environment | |
| `groups` | map of exactly `owner`, `developer`, `analyst`, `writer` → group name | `^role-[a-z][a-z0-9]{1,19}-<role>$`, where the suffix equals the key |
| `access` | role → environment → DataLevel | every role and environment present |
| `materialized_views` | role → environment → MvLevel | every role and environment present |
| `apps` | AppMapping | |
| `writer_user` | WriterUser | |

## Environment
| Field | Rule |
|---|---|
| `catalog` | must be the shared catalog: `prod` → `lakehouse`, `uat` → `lakehouse_uat`, `dev` → `lakehouse_dev` |
| `namespace` | `^[a-z][a-z0-9_]{1,63}$` |
| `bucket` | S3 rules: 3–63 characters of lowercase letters, digits, and `-`; it starts and ends with a letter or digit, and is not an IP address |
| `mv_database` | `^[a-z][a-z0-9_]{1,63}$` |

## Levels
| DataLevel | Meaning |
|---|---|
| `none` | no access in that environment |
| `read` | list and read tables |
| `write` | read, create tables, write data and table properties; no drops |
| `manage` | write, plus drop and full table and view metadata |

| MvLevel | Meaning |
|---|---|
| `none` | no access |
| `read` | select from the MVs |
| `author` | read, plus create, alter, refresh, and drop MVs |
| `manage` | everything on the MV database |

## AppMapping
| Field | Rule |
|---|---|
| `jupyterhub` | a list of role keys admitted to JupyterHub |
| `airflow` | role key → `Admin`, `User`, or `Viewer`; an omitted role gets no access |
| `jenkins` | role key → list of permissions from the allow-list: `Overall/Administer`, `Overall/Read`, `Job/Read`, `Job/Build`, `Job/Cancel`, `Job/Workspace`, `Job/Configure`, `Job/Create`, `Job/Delete`, `View/Read` |

## WriterUser
| Field | Rule |
|---|---|
| `username` | `^srv-[a-z0-9][a-z0-9-]{1,40}$` |
| `password_file` | a relative path under `.runtime/credentials/` without `..` |

## AppliedState (`.runtime/state/data-products/<name>.json`, mode 0600)
`name`, `environments` (namespace, bucket, MV database per environment), `groups`, `writer_user.username`, `applied_at`. Only names are recorded, no secrets.

## Derived names
| Object | Derived from | Example (`sales`) |
|---|---|---|
| Polaris principal role and Keycloak Polaris client role | group | `role-sales-owner` |
| Polaris catalog role | `<group>-<catalog>-catalog` | `role-sales-owner-lakehouse-catalog` (today's pattern) |
| StarRocks role | group, with `-` → `_` | `role_sales_owner` |
| RustFS policy | group | `role-sales-owner` |
| Bucket allowed location | `s3://<bucket>/<catalog>/` | `s3://bucket-sales/lakehouse/` |
| Namespace location | `s3://<bucket>/<catalog>/<namespace>/` | `s3://bucket-sales/lakehouse/sales_lh/` |

## Relationships
- A product has 3 environments, 4 groups, and 1 writer user.
- A group maps to one Polaris principal role, up to three catalog roles (one per environment where its level is not `none`), one StarRocks role, and one RustFS policy.
- `role-platform-admin` maps to every product's owner (Keycloak client roles, Polaris principal roles). It has its own StarRocks role (catalog-wide manage) and its own RustFS policy (manage on every product bucket).
- `srv-starrocks` is a member of every product's writer group.
