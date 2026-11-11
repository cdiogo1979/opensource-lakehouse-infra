# Data products

Reference for platform admins, owners and developers: where each product's data lives, the file that defines a product, what each access level allows, and how materialized views accelerate queries. Back to the [README](../../README.md); the components are in [Components](../components.md).

A data product is a set of data that one team owns and delivers for others, with its three environments, four roles, optional repository and the services the platform provisions for it ([definition](../../README.md#data-products)).

## Data layout

Every data product has three environments in the **shared** Polaris catalogs, each with its own namespace, bucket, and StarRocks MV database. The `default` product:

| Environment | Polaris catalog | Namespace | Bucket | StarRocks MV database |
|---|---|---|---|---|
| Production | `lakehouse` | `default_lh` | `bucket-default` | `default_lh` |
| UAT | `lakehouse_uat` | `default_lhuat` | `bucket-default-uat` | `default_lhuat` |
| Dev | `lakehouse_dev` | `default_lhdev` | `bucket-default-dev` | `default_lhdev` |

- **Paths**: tables live at `<bucket>/<catalog>/<namespace>/<table>`, for example `s3://bucket-default/lakehouse/default_lh/bootstrap_smoke_test/`.
- **Smoke tables**: each environment has a one-row `bootstrap_smoke_test` table, created by the product bootstrap.
- **Credentials**: no workload ever receives RustFS root keys. Polaris issues short-lived, table-scoped credentials (one hour, cached for 10 minutes). Streaming jobs also get a checkpoint key limited to their bucket's `checkpoints/` (see [Streaming checkpoints](streaming-checkpoints.md)).
- **Other products**: a product `sales` uses `sales_lh`, `sales_lhuat`, `sales_lhdev` in the same catalogs, in the buckets `bucket-sales`, `bucket-sales-uat`, `bucket-sales-dev`. Each catalog allows every product's bucket.

## Data product file

Each data product, `default` included, is one YAML file in `data-products/` that holds its whole configuration. Every component reads these files, so the file is the single place to look at or change a product:

```yaml
apiVersion: lakehouse.local/v1
name: sales
description: The sales data product
environments:              # catalogs are the shared ones; the rest is the product's
  prod: {catalog: lakehouse, namespace: sales_lh, bucket: bucket-sales, mv_database: sales_lh}
  uat: {catalog: lakehouse_uat, namespace: sales_lhuat, bucket: bucket-sales-uat, mv_database: sales_lhuat}
  dev: {catalog: lakehouse_dev, namespace: sales_lhdev, bucket: bucket-sales-dev, mv_database: sales_lhdev}
groups:                    # Keycloak groups, role-<token>-<role>
  owner: role-sales-owner
  developer: role-sales-developer
  analyst: role-sales-analyst
  writer: role-sales-writer
access:                    # none, read, write, manage: Polaris, StarRocks, and RustFS
  owner: {prod: manage, uat: manage, dev: manage}
  developer: {prod: read, uat: read, dev: write}
  analyst: {prod: read, uat: none, dev: none}
  writer: {prod: write, uat: write, dev: write}
materialized_views:        # none, read, author, manage (StarRocks MV databases)
  owner: {prod: manage, uat: manage, dev: manage}
  developer: {prod: read, uat: read, dev: author}
  analyst: {prod: read, uat: none, dev: none}
  writer: {prod: author, uat: author, dev: author}
apps:
  jupyterhub: [developer, analyst]
  airflow: {owner: User, developer: User, analyst: User, writer: Viewer}
  jenkins:                 # rights on the product's Jenkins folder; the owner is always its admin
    developer: [Job/Read, Job/Build, Job/Cancel, Job/Workspace]
    analyst: [Job/Read]
writer_user:
  username: srv-sales-writer
  password_file: .runtime/credentials/srv-sales-writer-password
repo:                      # optional: the product's DAG and CI repository (read anonymously)
  url: https://github.com/cdiogo1979/opensource-lakehouse-sample-dp.git
  prod_branch: main
  uat_branch: uat
```

**The `repo` block** (optional) gives the product its own Airflow DAG bundles: `<name>-main` tracks `prod_branch` and `<name>-uat` tracks `uat_branch`. The URL must be credential-free `https`; the repository is read without credentials. Several products may share one repository. `default` uses `opensource-lakehouse-sample-dp` (`main` and `uat`). There is no writer field: runs from a product's bundles always write as that product's `writer_user` (see [Airflow](airflow.md)). The same block gives the product its Jenkins jobs `<name>_ci` and `<name>_cd` (see [Jenkins](jenkins.md)).

## Access levels

| Level | Polaris (on the product namespace) | StarRocks (on the product database) | RustFS (on the product bucket) |
|---|---|---|---|
| read | list and read tables and views | `SELECT` | read |
| write | read, plus create tables and write data | read, plus `INSERT` and `CREATE TABLE` | read and write |
| manage | write, plus drop and full table and view metadata | `ALL` on the database and its tables | all actions |

- **Isolation**: product roles reach only their own namespaces, databases, and buckets. Anyone with access to a catalog can see every product's namespace **names**, but not their tables or data.
- **No namespace management**: product roles cannot create, drop, or move namespaces. Each product has exactly the three namespaces in its file.
- **Platform admin**: `role-platform-admin` is owner of every product.
- **Airflow is platform-wide**: it has no per-product permissions, so the Airflow roles in any product's file apply to the whole Airflow. Owners and developers are `User` (run, pause, and clear DAGs, read logs), and only `role-platform-admin` is `Admin`.
- **Jenkins is per folder**: each product's owners are admins of its folder (jobs, runs, views, folder credentials), and `apps.jenkins` grants the other roles rights on that folder only. Product groups can read Jenkins but see no other product's folder. Only `role-platform-admin` and the break-glass account administer Jenkins. `apps.jenkins` refuses `owner` and any `Overall/*` permission.

What each bootstrap group can do in every app: [Identity — what each group can do](identity.md#what-each-group-can-do).

## Materialized views and query acceleration

StarRocks materialized views (MVs) are part of query acceleration for **everyone**: StarRocks rewrites a query on the Iceberg tables to read a matching materialized view, so users keep querying the tables as usual and get faster answers. Each product and environment has an MV database in StarRocks' `default_catalog` (`default_lh`, `default_lhuat`, `default_lhdev` for `default`), with the levels from `materialized_views` above.

- **Who authors them**: developers in dev, and the writer in every environment (from workloads); owners and platform admins manage them. See the [developer journey](../journeys/data-product-developer.md#7-accelerate-queries-with-materialized-views).
- **Who benefits**: every user whose query can be answered from a view they may read; see the [analyst journey](../journeys/data-analyst.md#4-faster-queries-through-materialized-views).
- The rewrite behavior on this platform is to be verified by a follow-up intent.
