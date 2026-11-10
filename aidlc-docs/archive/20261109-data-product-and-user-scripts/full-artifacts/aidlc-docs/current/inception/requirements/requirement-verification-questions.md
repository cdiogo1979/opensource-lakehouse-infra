# Requirement Verification Questions — Data Product and User Scripts

Answer each question by putting the letter after the `[Answer]:` tag.

## Question 1 — Catalog model for a new product
How should a new data product be laid out in Polaris?

A) Own catalogs per product and environment, `<product>`, `<product>_uat`, `<product>_dev`, each stored in its own bucket. Today's catalog-wide grants isolate the products, and `default` is unchanged (Recommended)

B) Share the environment catalogs (`lakehouse`, `lakehouse_uat`, `lakehouse_dev`) with one namespace per product. This needs extra allowed storage locations and namespace-scoped grants, and changes how `default` is granted

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 2 — Naming and name rules
How should the product's resources be named?

A) Follow the `default` pattern:
- groups `role-<product>-{owner,developer,analyst,writer}`
- buckets `bucket-<product>`, `bucket-<product>-uat`, `bucket-<product>-dev`
- catalogs `<product>`, `<product>_uat`, `<product>_dev`
- namespaces `<product>_lh`, `<product>_lhuat`, `<product>_lhdev`
- StarRocks roles `role_<product>_*` and MV databases named like the namespaces

The product name is lowercase letters and digits, starting with a letter, 2–20 characters, with no hyphens or underscores, so every derived name stays unambiguous. `default`, `lakehouse`, and reserved words are refused (Recommended)

B) Allow hyphens in product names and convert them to underscores where needed

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3 — Which services grant access for a new product's groups
Where should a new product's groups give access?

A) The data services only: Polaris catalogs, RustFS buckets and console, and StarRocks catalogs, roles, and MV databases. JupyterHub admission, Airflow UI roles, and Jenkins stay as they are for now. Developers and analysts reach the new product from JupyterHub only if they are also in a `default` group (Recommended for a small intent)

B) The data services, plus JupyterHub admission for any product's developer and analyst groups

C) The data services, plus JupyterHub, Airflow, and Jenkins mappings for every product

X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 4 — Writer and service identities
What identities should a new product get?

A) No new writer user. `srv-starrocks` joins the product's writer group so StarRocks can read and write its catalogs, and `platform-admin` gets owner rights on it. Airflow writes stay on `default` (Recommended)

B) Also create a writer user `srv-<product>-writer`, with its password file in `.runtime/credentials`

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 5 — Where the list of products is kept
How should the platform remember which products exist?

A) A tracked file, `infra/data-products.json`, listing every product (`default` included). The product script adds the new product to it, and every bootstrap, reconciler, and the product bootstrap read it, so a reset and rebuild recreate all products (Recommended)

B) Discover products from Keycloak groups at run time; there is no file

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6 — Product script behavior on rerun
What should happen when the product script runs for a product that already exists?

A) Idempotent: create what is missing, accept what matches, and refuse conflicts without changing them. A `--dry-run` shows the plan (Recommended)

B) Refuse if the product already exists in any service

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 7 — New user script
How should the user script handle the password and profile?

A) Required: username and email. Optional: first and last name. The password is prompted for without echo (or read with `--password-file`) and is **temporary** by default, so Keycloak asks the user to change it at first login; `--permanent` makes it permanent. No groups are assigned (Recommended)

B) Use the default password `ChangeM3!`, permanent, like the bootstrap users

C) Generate a random temporary password and print it once

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 8: Security Extensions
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)

B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 9: Property-Based Testing Extension
Should property-based testing (PBT) rules be enforced for this project?

A) Yes — enforce all PBT rules as blocking constraints (recommended for projects with business logic, data transformations, serialization, or stateful components)

B) Partial — enforce PBT rules only for pure functions and serialization round-trips (suitable for projects with limited algorithmic complexity)

C) No — skip all PBT rules (suitable for simple CRUD applications, UI-only projects, or thin integration layers with no significant business logic)

X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 10: Resiliency Extensions
Should the resiliency baseline be applied to this project?

A) Yes — apply the resiliency baseline as directional best practices and design-time guidance (recommended for business-critical workloads, as an informed starting point that you can validate and harden before go-live)

B) No — skip the resiliency baseline (suitable for PoCs, prototypes, and experimental projects where rapid iteration matters more than reliability)

X) Other (please describe after [Answer]: tag below)

[Answer]: B
