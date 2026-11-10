# Application Design — Data Product and User Scripts

Consolidates [components.md](components.md), [component-methods.md](component-methods.md), [services.md](services.md), and [component-dependency.md](component-dependency.md). The decisions are in [application-design-plan.md](../plans/application-design-plan.md): AD-Q1..Q4 and CR-Q1..Q6.

## Summary
- **The platform becomes multi-product.** Each product, `default` included, is one YAML file in `data-products/`. Every component reads those files, so nothing hard-codes `default` any more.
- **Products share the three environment catalogs**, each in its own namespaces and buckets. Polaris grants are namespace-scoped and StarRocks grants database-scoped, for every product.
- **Three operator scripts**:
  - **create and apply**: `--init`, then apply a file
  - **remove**: refused for `default`; data is kept unless `--purge-data`
  - **create user**: no groups
- **Restarts**:
  - **in this intent**: Polaris once; Jenkins, JupyterHub, and Airflow once each, for their new mounts
  - **per product change**: only Jenkins

## Decisions
| ID | Decision |
|---|---|
| AD-Q1 | Enable `polaris.features."ALLOW_NAMESPACE_CUSTOM_LOCATION"=true` server-wide. It was probed: the per-catalog property and the `behavior-changes` form are ignored. Tables stay confined to the catalog's allowed locations |
| AD-Q2 | Polaris OIDC filter: the fixed pattern `^role-[a-z][a-z0-9]{1,19}-(developer\|analyst\|owner\|writer)$` |
| AD-Q3 | JupyterHub and Airflow map groups from the mounted product files at each sign-in, with no restart. Jenkins uses a CasC file rendered from the files, and restarts on change |
| AD-Q4 | `NAMESPACE_LIST` on each shared catalog: every product's namespace names are visible; contents are not |
| CR-Q1 | The product file holds the full configuration, all editable within the rules below |
| CR-Q2 | `--init <name>` writes the standard file; applying a file converges, including revokes |
| CR-Q3 | Removal refuses while data exists unless `--purge-data`. It needs the typed name or `--yes`. Users stay |
| CR-Q4 | Group names must match the pattern above |
| CR-Q5 | Catalogs must be the shared environment catalogs |
| CR-Q6 | Names are locked once applied |

## Product file format (`data-products/sales.yaml`, as `--init sales` writes it)
```yaml
apiVersion: lakehouse.local/v1
name: sales
description: Sales data product
environments:
  prod: {catalog: lakehouse,     namespace: sales_lh,    bucket: bucket-sales,     mv_database: sales_lh}
  uat:  {catalog: lakehouse_uat, namespace: sales_lhuat, bucket: bucket-sales-uat, mv_database: sales_lhuat}
  dev:  {catalog: lakehouse_dev, namespace: sales_lhdev, bucket: bucket-sales-dev, mv_database: sales_lhdev}
groups:
  owner: role-sales-owner
  developer: role-sales-developer
  analyst: role-sales-analyst
  writer: role-sales-writer
# Data access per role and environment (none, read, write, manage), applied to
# Polaris namespaces, StarRocks databases, and RustFS buckets.
access:
  owner:     {prod: manage, uat: manage, dev: manage}
  developer: {prod: read,   uat: read,   dev: write}
  analyst:   {prod: read,   uat: none,   dev: none}
  writer:    {prod: write,  uat: write,  dev: write}
# StarRocks materialized-view databases (none, read, author, manage).
materialized_views:
  owner:     {prod: manage, uat: manage, dev: manage}
  developer: {prod: read,   uat: read,   dev: author}   # CR-2
  analyst:   {prod: read,   uat: none,   dev: none}
  writer:    {prod: author, uat: author, dev: author}
apps:
  jupyterhub: [developer, analyst]
  airflow: {owner: Admin, developer: User, analyst: User, writer: Viewer}
  jenkins:
    owner: [Overall/Administer]
    developer: [Overall/Read, Job/Read, Job/Build, Job/Cancel, Job/Workspace]
    analyst: [Overall/Read, Job/Read]
writer_user:
  username: srv-sales-writer
  password_file: .runtime/credentials/srv-sales-writer-password
```

## Validation rules
**Product name**: 2–20 lowercase letters or digits, starting with a letter. It must not be a reserved word (`lakehouse`, `platform`, `admin`, `srv`, `starrocks`, `polaris`).

**Field rules**:

| Field | Rule |
|---|---|
| bucket | a valid S3 name |
| namespace and MV database | `[a-z][a-z0-9_]{1,63}` |
| groups | match the group pattern |
| writer username | `srv-[a-z0-9-]+` |
| password file | stays under `.runtime/credentials/` |
| levels | come from the allowed sets |
| app roles | Airflow roles are `Admin`, `User`, or `Viewer`; Jenkins permissions come from an allow-list |

**Across files**: no shared bucket, namespace, MV database, group, or writer user, and the file name equals `name`. `default.yaml` keeps today's names and today's matrix exactly.

## Platform-wide effects (documented in the README)
- **Owners of any product are Airflow Admin and Jenkins Administer** across the platform (FR-7), unless their file says otherwise.
- **`role-platform-admin` owns every product.** Its client roles include each `role-<p>-owner`; its RustFS policy covers every product bucket; it is the Hub admin.
- **`srv-starrocks` is in every product's writer group.** StarRocks roles narrow access per product.

## Risks
| Risk | Mitigation |
|---|---|
| `default` users lose access, or gain too much, during the grant migration | Functional Design sets an add-verify-revoke order; Build and Test compares effective access before and after |
| The server-wide namespace-location flag lets catalog admins place namespaces anywhere | Only bootstrap and service roles create namespaces. Product roles have no `NAMESPACE_CREATE`, and tables outside the allowed locations are still refused (probed) |
| A partial create or remove | Every step is idempotent, and removal deletes the product file last, so a rerun finishes the job |
| A bad file blocks sign-ins | JupyterHub and Airflow fail closed to platform admins only, and the apply validates before any change |

## Canonical knowledge impact (unchanged from the execution plan)
At closure, update `application-design.md`, `lakehouse-product-access.md`, `starrocks-sql-access.md`, and `jenkins-ci-access.md`.
