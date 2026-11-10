# Domain Entities — airflow-bundles

## Repo (`repo` in `data-products/<name>.yaml`, optional)
| Field | Rule |
|---|---|
| `url` | `https://<host>/<path>`. No user, password, port, query, or fragment; host and path in the safe URL character set; at most 300 characters |
| `prod_branch` | A Git ref name: `^[A-Za-z0-9][A-Za-z0-9._/-]{0,99}$`; no `..`, `//`, `@{`; not ending in `/`, `.`, or `.lock` |
| `uat_branch` | Same rule. It may equal `prod_branch` |

Unknown keys are refused, like everywhere in the product file.

## Bundle (generated, one pair per product with a repo)
| Field | Prod | UAT |
|---|---|---|
| `name` | `<name>-main` | `<name>-uat` |
| `classpath` | `airflow.providers.git.bundles.git.GitDagBundle` | same |
| `kwargs.repo_url` | `repo.url` | same |
| `kwargs.tracking_ref` | `repo.prod_branch` | `repo.uat_branch` |
| `kwargs.git_conn_id` | `lakehouse_git` | same |
| `kwargs.refresh_interval` | 300 | same |
| `kwargs.sparse_dirs` | `["dags", "configs", "notebooks"]` | same |

**Order**: `default` first, then products by name; prod before UAT.

## DagRef (parsed from a DAG ID)
- `DAG_ID_PATTERN = ^(?P<product>[a-z][a-z0-9]{1,19})-(?P<env>main|uat)-(?P<workload>.+)$`.
- `env`: `main` is the prod bundle, `uat` the UAT bundle. The expected bundle is `f"{product}-{env}"`.

## Writer (staged for the broker; one per product with a repo)
`product`, `username` (= `writer_user.username`), `group` (= `groups.writer`), `password_file` (the staged file name).

## WritersFile (`.runtime/container-mounts/airflow-writers/writers.json`)
`{"<product>": {"username": …, "group": …, "password_file": "<username>-password"}}`. No password values.

## Fingerprint (`.runtime/state/airflow-bundles.json`)
SHA-256 of the canonical bundle list plus the sorted writer set (product, username, group), and of each staged password file's contents. The digest is stored, never the passwords.
