# Requirements — Data Product Airflow Bundles

## Intent Analysis
- **User request**: "we will now add a new config on the data-product yaml - repo (for the default and testing dp you can use https://github.com/cdiogo1979/opensource-lakehouse. This config will be used to create the airflow bundles . the config should also have the name of the prod and uat branches . this is read only so no credentials are needed. when a new data product is created and the repo is set the airflow bundles should execute. if possible also the credential/secret name to be used in airflow to write should also be part of the data product configuration"
- **Discussion**: the write credential is derived from the DAG ID. DAG IDs start with the product name ("default-main-test_environment" uses the default writer), and the broker checks with Airflow that the DAG belongs to that product's bundle.
- **Type**: extension of the data product model, the Airflow bundle configuration, and the writer token broker, plus a patch for the workload repository.
- **Answers**: Q1 A, Q2 clarified (C1), Q3 B, Q4 A, Q5 A, C2 A. Change CR-1: no writer setting in the file; the writer follows from the product name.

## Functional Requirements

### FR-1 Product file (C1)
- **`repo`** (optional): `{url, prod_branch, uat_branch}`.
  - `url`: credential-free `https://` with no user or password.
  - Branches: valid Git ref names.
  - No credentials anywhere; the bundles read the repository anonymously through the existing `lakehouse_git` connection.
- **No writer setting (CR-1)**: the write credential follows from the product name. A DAG ID starting with `<name>-main-` or `<name>-uat-` uses that product's existing writer user (`writer_user`, `srv-<name>-writer` by default, whose password the platform holds in `writer_user.password_file`).
- **`default.yaml` and the test product**: `repo: {url: https://github.com/cdiogo1979/opensource-lakehouse.git, prod_branch: main, uat_branch: uat}`.
- **Template**: `--init` writes the same `repo` block, commented out.
- **Names are product-based**: bundles and DAG prefixes come from the product `name` in the file, not from the repository.

### FR-2 Bundles from the product files
- **Two bundles per product with a repo**:
  - `<name>-main` tracks `prod_branch` and is the prod environment
  - `<name>-uat` tracks `uat_branch` and is the UAT environment

  Settings are as today: `GitDagBundle`, `lakehouse_git`, a 300 s refresh, sparse `dags`, `configs`, `notebooks`.
- **Generation**: `airflow-bundle-config.py` generates the list from every product file. `validate-bundle-config.py` accepts exactly that generated list (pairs consistent with the files) and keeps every other check.
- **Default renamed now (Q3 B)**: `lakehouse-main`/`lakehouse-uat` become `default-main`/`default-uat`. Old bundle checkouts and DAG history are left in place.

### FR-3 Applying and removing
- **Apply**: after the other steps, `create-data-product.sh` regenerates the bundle list. If it changed and Airflow is running, the Airflow services are recreated with the new list. Airflow then clones the repository and loads the DAGs (Q4 A); no DAG run is started.
  - `--no-restart` prints the command instead.
  - `--dry-run` shows the bundle changes.
- **Remove**: `remove-data-product.sh` removes the product's bundles the same way.
- **Start**: `lakehouse.sh start-airflow` uses the generated list.

### FR-4 Writer broker per product (Q1 A)
- **Credentials**: the broker holds the writer credential (the product's `writer_user`: username plus password file, staged read-only for the broker only) of every product with a `repo`. It never exposes them to DAGs.
- **Product from the DAG ID**: it is the text before `-main-` or `-uat-` (product names have no hyphens). An unknown or unprefixed DAG ID is refused.
- **Airflow check**: the broker asks Airflow, through a dedicated read-only Airflow identity, for the DAG's bundle, which must be `<product>-main` or `<product>-uat`. Otherwise registration is refused.
- **Token check**: the issued token must carry that product's writer group role (replacing the fixed `role-default-writer` check).
- **Renewal**: as today, per run.
- **Credential changes**: a product apply or remove that changes the set of credentials restages them and recreates the broker.

### FR-5 Workload-repository patch (C2 A)
- A patch for `opensource-lakehouse`, delivered in this intent, that makes:
  - `dags/dag_defaults.py` recognise `<product>-main`/`<product>-uat` (environment prod or UAT, DAG prefix = bundle name)
  - DAG IDs `<bundle>-<workload>`
  - product-specific configs: `configs/<product>/<env>.yml`, falling back to `configs/<env>.yml` for `default`
- **Testing**: it is checked against the local bundle checkout (the repository's own tests, where they run locally).
- **Pushing**: the user reviews and pushes it. Until then, `default`'s DAGs load as `dev` with colliding IDs. Build and Test records that state.

### FR-6 Documentation and tests
- **README**: the `repo` block, bundle naming, how the write credential follows from the product name, the workload contract.
- **Tests**: contract tests and Hypothesis properties:
  - the bundle list round-trips through rendering and validation
  - each product with a repo gets exactly two bundles
  - the DAG ID maps to the right product, with unknown or other-product IDs refused

## Change request CR-1 (2026-11-09, during Requirements Analysis)
> "no need to set the writer in the yml , as its derived from the name of the data product"

The `airflow.writer` field is dropped. The product named by the DAG-ID prefix supplies its own `writer_user`.

## Non-Functional Requirements
- **Secrets**:
  - no Git credentials, no writer passwords in Airflow, DAGs, Compose files, or output
  - the broker's Airflow identity has read-only API rights
- **Isolation**: a DAG can only obtain the writer of the product whose bundle contains it.
- **Restarts**: only the Airflow services, and only when the bundle list or the credential set changes.
- **Idempotency**: rerunning an apply with no change recreates nothing.
- **Verified live**:
  - default's bundles renamed and loading
  - a test product with the same repository gets its two bundles
  - the broker issues the right writer for a correctly prefixed, correctly bundled DAG, and refuses a mismatched prefix
  - the applied patch (if pushed), or the documented interim state

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q5: A) |
| Property-Based Testing | Partial (PBT-02, 03, 07, 08, 09 enforced) | Requirements Analysis (Q5: A) |
| Resiliency Baseline | No | Requirements Analysis (Q5: A) |

## Out of scope
- Git credentials or private repositories.
- Triggering DAG runs.
- Changing `opensource-lakehouse` directly; a patch is delivered instead.
- Per-product Airflow UI permissions.
