# Requirement Verification Questions — StarRocks Integration

Answer each question by putting the letter after the `[Answer]:` tag.

## Question 1 — Image and topology
Which StarRocks image and topology should run in the separate Compose file?

A) The latest stable StarRocks 4.x upstream images, pinned by digest: one FE and one BE (shared-nothing), with the arm64 image confirmed in design (Recommended)

B) StarRocks 4.1.6, the version the legacy role design was tested on, as one FE and one BE without the Kerberos layers

C) The single-container `allin1` image (FE and BE together); smallest footprint, less like a real deployment

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2 — How people log in to StarRocks
How should the bootstrap users sign in to StarRocks SQL?

A) StarRocks native users for the five bootstrap users, with the same default password `ChangeM3!` and roles from their Keycloak group; `bootstrap-users.sh` also resets them to their defaults (Recommended)

B) Keycloak JWT login: users present a Keycloak access token as the password, and roles follow their groups. The newest feature, which must be confirmed for the chosen version; awkward with ordinary SQL clients

C) Both: native users now, plus JWT login for Keycloak users

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 3 — StarRocks identity toward Polaris
Which identity should the StarRocks Iceberg catalogs use to call Polaris?

A) A new Keycloak service user `srv-starrocks` in `role-default-writer` (read and write on all three catalogs), with each StarRocks user's access narrowed by StarRocks roles (Recommended)

B) Reuse `srv-default-writer`, the Airflow and Spark writer

C) A new service user with read-only Polaris access (StarRocks would not write to Iceberg tables)

D) Pass each user's own Keycloak token through to Polaris, if the chosen version supports it, so Polaris enforces per-user access

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4 — Object storage credentials
How should StarRocks read and write data files in RustFS?

A) Polaris-vended, short-lived credentials, the same path Spark uses (Recommended; confirm StarRocks support in design)

B) A dedicated RustFS access key for StarRocks with a policy limited to the three buckets

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5 — Role names and access matrix
How should StarRocks roles align with the product roles?

A) StarRocks roles named after the Keycloak groups (`role_default_owner`, `role_default_developer`, `role_default_analyst`, `role_default_writer`, `role_platform_admin`; underscores in case StarRocks rejects hyphens), with the same matrix as Polaris: owner manage all; developer read prod and UAT, read and write dev; analyst read prod; writer read and write all (Recommended)

B) Keep the legacy names (`lakehouse_developer`, `lakehouse_analyst`, `lakehouse_writer`) and add owner and platform admin

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6 — Platform admin in StarRocks
What should `role-platform-admin` get in StarRocks?

A) Owner data rights plus StarRocks system administration (users, roles, catalogs, cluster), matching its Keycloak realm-admin and Hub-admin rights (Recommended)

B) Owner data rights only; StarRocks administration stays with `root`

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 7 — Materialized-view databases
Should the bootstrap also create internal StarRocks databases for materialized views?

A) Yes: `default_lh`, `default_lhuat`, `default_lhdev` in the internal catalog. Writer manages materialized views in all three, developer reads all three, analyst reads production, and owner and platform admin manage all of them

B) No; external Iceberg catalogs only for now (Recommended for a first integration)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 8 — Lifecycle and bootstrap
How should StarRocks start, and when should its catalogs and roles be created?

A) Its own commands `lakehouse.sh start-starrocks | starrocks-status | stop-starrocks`, like Airflow. `start-starrocks` applies the catalogs, users, and roles. `bootstrap-default-product.sh` also applies them when StarRocks is running and skips them with a notice when it is not. The reset includes StarRocks (Recommended)

B) Always started and bootstrapped by `bootstrap-default-product.sh`, which starts the StarRocks Compose file itself

C) Part of the core `lakehouse.sh start`

X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 9: Security Extensions
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)

B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 10: Property-Based Testing Extension
Should property-based testing (PBT) rules be enforced for this project?

A) Yes — enforce all PBT rules as blocking constraints (recommended for projects with business logic, data transformations, serialization, or stateful components)

B) Partial — enforce PBT rules only for pure functions and serialization round-trips (suitable for projects with limited algorithmic complexity)

C) No — skip all PBT rules (suitable for simple CRUD applications, UI-only projects, or thin integration layers with no significant business logic)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 11: Resiliency Extensions
Should the resiliency baseline be applied to this project?

A) Yes — apply the resiliency baseline as directional best practices and design-time guidance (recommended for business-critical workloads, as an informed starting point that you can validate and harden before go-live)

B) No — skip the resiliency baseline (suitable for PoCs, prototypes, and experimental projects where rapid iteration matters more than reliability)

X) Other (please describe after [Answer]: tag below)

[Answer]: B
