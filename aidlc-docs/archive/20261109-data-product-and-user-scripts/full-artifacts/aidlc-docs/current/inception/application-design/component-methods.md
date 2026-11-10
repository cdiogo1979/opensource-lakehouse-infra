# Component Methods — Data Product and User Scripts

Signatures and purpose only. The business rules (grant sets, the migration order, conflict rules) are defined in Functional Design.

## C1 Product model (`infra/products/data_products.py`)
| Method | Input → Output | Purpose |
|---|---|---|
| `load_product(path) -> Product` | YAML file → frozen dataclass | Parse with `yaml.safe_load` and validate the schema, the name rules, the group pattern, and the shared catalogs |
| `load_all(directory=data-products) -> list[Product]` | directory → products | Load every `*.yaml` file and check collisions across products |
| `render_template(name) -> str` | product name → YAML text | The standard file for `--init` (the `default` conventions applied to `name`) |
| `check_collisions(products) -> None` | products → raises | No bucket, namespace, MV database, group, or writer user is shared |
| `check_locked_names(product, state) -> None` | product and applied state → raises | Refuse a renamed bucket, namespace, group, or writer user |
| `read_state(name) / write_state(product)` | `.runtime/state/data-products/<name>.json` | The applied names (mode 0600, atomic write) |
| `group_pattern() -> re.Pattern` | none | `^role-[a-z][a-z0-9]{1,19}-(owner\|developer\|analyst\|writer)$`, shared by Polaris, JupyterHub, and Airflow |

**`Product` fields**: `name`, `description`; `environments{prod,uat,dev}` (catalog, namespace, bucket, mv_database); `groups{owner,developer,analyst,writer}`; `access[role][env]` (`none`, `read`, `write`, `manage`); `materialized_views[role][env]` (`none`, `read`, `author`, `manage`); `apps` (JupyterHub-admitted roles, Airflow role per role, Jenkins permissions per role); `writer_user` (username, password file).

## Component script interface (C3, C5, C6, C7)
Every product-aware component script accepts the same arguments:

| Mode | Arguments | Purpose |
|---|---|---|
| apply | `--product FILE` (repeatable; the default is every file) `[--dry-run]` | Create what is missing and converge grants to the file |
| remove | `--remove --product FILE [--purge-data] [--dry-run]` | Remove the product's objects; refuse, listing them, if data exists and `--purge-data` is not given |
| inventory | `--inventory --product FILE` | Print counts of the product's tables, MVs, or objects (the removal preflight); names only, no data |

All modes are idempotent: a missing object on removal counts as already removed, so a failed removal can be rerun.

## C4 Create user (`infra/keycloak/create-user.py`)
`create-user.py <username> [--email E] [--first-name F] [--last-name L] [--password-file F]` creates the user, or exits 1 if the username exists. The password goes over stdin or a file, never as an argument.

## C9 Apps
| Method | Where | Purpose |
|---|---|---|
| `admitted_groups(products) -> frozenset` | `lakehouse_policy.py` | Groups that may enter JupyterHub, read at each sign-in. The Hub admin stays `role-platform-admin` |
| `group_role_mapping(products) -> dict` | `airflow_sso_roles.py` | Group to Airflow role, read at each sign-in |
| `render_jenkins_casc(products) -> str` | `infra/products/render_jenkins.py` | The CasC file with the static entries plus one entry per product group |

## C10 Operator scripts
- `create-data-product.sh --init <name>`
- `create-data-product.sh <file> [--dry-run] [--no-restart]`
- `remove-data-product.sh <name> [--purge-data] [--yes] [--dry-run] [--no-restart]`
- `create-user.sh <username> [--email] [--first-name] [--last-name] [--password-file]`
