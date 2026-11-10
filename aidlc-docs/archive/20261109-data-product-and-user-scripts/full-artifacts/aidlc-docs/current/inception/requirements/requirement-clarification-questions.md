# Requirement Clarification Questions — Data Product and User Scripts

These follow from the combined answers: Q1 B (shared catalogs), Q2 A (default naming pattern), Q3 C (all apps), and Q4 B (writer per product).

## Clarification 1 — Grants in shared catalogs
With shared catalogs, a product is a namespace (`<product>_lh`, `<product>_lhuat`, `<product>_lhdev`) in `lakehouse`, `lakehouse_uat`, and `lakehouse_dev`, stored in the product's own bucket. Grants must then be scoped per namespace. How should this apply?

A) Every product, `default` included, gets namespace-scoped grants with the same matrix as today:
- owner: everything in its namespaces, including drops
- developer: read prod and UAT, write dev
- analyst: read prod
- writer: write all

Each role gets only the catalog-level read needed to list namespaces. Platform admin keeps catalog-wide management. `default`'s existing catalog-wide grants are replaced by namespace-scoped ones, and its tables and data are untouched (Recommended)

B) New products get namespace-scoped grants, while `default` keeps its catalog-wide grants, so `default` roles can also see and change new products' data

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Clarification 2 — App permissions for new products
Airflow and Jenkins permissions are platform-wide, not per product. How should new products' groups map there?

A) The same mapping as `default` for every product:
- JupyterHub admits developer and analyst groups
- Airflow: owner Admin, developer and analyst User, writer Viewer
- Jenkins: owner Administer, developer build, analyst read

A new product's owner therefore becomes admin of the whole Airflow and Jenkins (Recommended for simplicity, documented)

B) JupyterHub as in A. In Airflow and Jenkins, new products' groups get read-only access (Viewer and read); only `default` owners and platform admins stay admins

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Clarification 3 — Per-product writer
The Airflow token broker only supports `srv-default-writer`. What is `srv-<product>-writer` for in this intent?

A) Create it, in the product's writer group with a password file in `.runtime/credentials`, ready for that product's future workloads. The Airflow broker is unchanged, so DAGs keep writing as `default`'s writer (Recommended)

B) Also extend the Airflow broker to issue a token for the product writer chosen by the DAG

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Clarification 4 — Applying a new product to running services
JupyterHub, Airflow, and Jenkins read their group mappings at start. The Polaris OIDC role filter changes once, and later reads every product's groups. What should the product script do?

A) Apply everything and restart only the affected running services (JupyterHub; Jenkins; Airflow if running; Polaris only when its filter changes), printing what it restarted. `--no-restart` skips the restarts and prints what to restart (Recommended)

B) Never restart; print which services must be restarted

X) Other (please describe after [Answer]: tag below)

[Answer]: A
