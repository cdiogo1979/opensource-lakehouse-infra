# Application Design Plan — Data Product and User Scripts

## Plan
- [x] Read requirements, the execution plan, the reverse-engineering coupling map, and the canonical designs
- [x] Probe the four design assumptions against the running stack (throwaway objects only; all removed)
- [x] Collect answers to the design questions below (AD-Q1..Q4, CR-1 questions CR-Q1..Q6)
- [x] Generate `components.md`
- [x] Generate `component-methods.md`
- [x] Generate `services.md`
- [x] Generate `component-dependency.md`
- [x] Generate the consolidated `application-design.md`
- [x] Validate completeness and consistency against FR-1..FR-10

## Probe results (2026-11-09)
| # | Assumption | Result | How it was checked |
|---|---|---|---|
| 1a | A catalog's allowed locations can be extended | **Confirmed.** `PUT /catalogs/{name}` with the entity version adds a second bucket | Throwaway catalog `aidlc_probe` on the live Polaris, then deleted |
| 1b | A namespace can live in another bucket | **Only with a server-wide flag.** Polaris 1.8 refuses a namespace `location` unless `polaris.features."ALLOW_NAMESPACE_CUSTOM_LOCATION"=true`. The per-catalog property is ignored, and the `polaris.behavior-changes` form is ignored too. With the flag, tables are created in the product bucket, and a table outside the allowed locations is still refused | Throwaway in-memory Polaris 1.8.0 on the same RustFS, then removed |
| 1c | Vended credentials for a namespace in the second bucket | **Confirmed.** `loadTable` with vended credentials returns storage credentials | Same throwaway Polaris |
| 2 | Polaris namespace-level grants | **Confirmed.** Grants on one namespace allowed list, load, create, write, and drop there. The same principal got 403 in another namespace, on namespace creation, and on drop without `TABLE_DROP`. `NAMESPACE_LIST` at catalog level lists **every** namespace name | Same throwaway Polaris |
| 3 | StarRocks database-scoped grants on an external Iceberg catalog | **Confirmed.** `SELECT`, `INSERT ON ALL TABLES IN DATABASE`, and `CREATE TABLE`/`ALL ON DATABASE` are accepted. The user sees only its database and reads it; other databases are refused | Throwaway role and password user on the live StarRocks, then dropped |
| 4 | Jenkins configuration can be generated per product | **Confirmed by inspection.** `jenkins.yaml` is mounted from `infra/jenkins/casc/`; it can be rendered into `.runtime/container-mounts/` like `polaris-application.properties`. The matrix has no wildcard group entries | Read of `compose.jenkins.yml` and the CasC file |

## Design questions

### AD-Q1 Polaris namespace location flag
Shared catalogs with a bucket per product need `ALLOW_NAMESPACE_CUSTOM_LOCATION` on the server. It is set once in `infra/polaris/oidc.properties` (the Polaris settings template) and needs one Polaris restart during this intent. Tables are still confined to the catalog's allowed locations.

A) Enable the flag server-wide (Recommended)
B) Drop the bucket-per-product rule: products share the environment buckets, in their own prefix
X) Other (please describe after [Answer]: tag below)

[Answer]: A — Enable the flag server-wide

### AD-Q2 Polaris OIDC role filter
A) A fixed pattern that accepts any product's four groups (`^role-[a-z][a-z0-9]{1,19}-(developer|analyst|owner|writer)$`). One restart now; a new product needs no Polaris restart. A group only gains access through the Polaris roles the product script creates. (Recommended)
B) Generate the exact list from the registry. Polaris restarts on every new product
X) Other (please describe after [Answer]: tag below)

[Answer]: A — Fixed name pattern

### AD-Q3 App mappings (JupyterHub, Airflow, Jenkins)
A) JupyterHub and Airflow match product groups by the same name pattern, so no restart is needed. Jenkins has no pattern support, so its CasC file is generated from the registry and Jenkins restarts after a new product (Recommended)
B) Generate all three from the registry, and restart all three on every new product
C) Jenkins through Keycloak client roles (`jenkins-admin`, `jenkins-developer`, `jenkins-analyst`) assigned to the product groups, so no app restarts at all. This changes the Jenkins sign-in claim
X) Other (please describe after [Answer]: tag below)

[Answer]: A — Pattern for JupyterHub and Airflow; Jenkins generated with a restart. Refined by CR-1: JupyterHub and Airflow read the mounted product files at sign-in, so app mappings stay editable without restarts

### AD-Q4 Namespace names across products
With namespace-scoped grants, listing namespaces needs `NAMESPACE_LIST` on the catalog, which shows every product's namespace names (not their tables or data). StarRocks shows only granted databases.

A) Accept: names are visible, contents are not (Recommended)
B) Do not grant `NAMESPACE_LIST`. Clients must address namespaces by name; Spark `SHOW NAMESPACES` and some tools stop working
X) Other (please describe after [Answer]: tag below)

[Answer]: A — Accept: names visible, contents not

## Design notes (no answer needed)
- **Platform admin**: maps to `role-<p>-owner` in every product (Keycloak client roles), as `default` does today, in place of a separate catalog-wide role.
- **Owners lose `CATALOG_MANAGE_ACCESS`**. Access changes go through Keycloak groups, as today.
- **`srv-starrocks`** joins every product's writer group, so the shared StarRocks catalogs can reach every namespace. StarRocks roles then narrow access per product.

## Change request CR-1 (user, during Application Design)
> "also a script to remove the dataproduct (which cannot be the default) should be added , which removes all artifacts. in order to make it more modular , each data product , includoing the default should have a yaml file on all configurations are stored. the creation script to invoke that yaml file"

### CR-Q1 YAML content
[Answer]: Full file, everything editable (names, access levels, app mappings, writer user)

### CR-Q2 Create flow
[Answer]: Init, then apply the file (`--init <name>` writes a standard file; applying a file reconciles it, including revokes after edits)

### CR-Q3 Data on removal
[Answer]: Refuse while tables or objects exist unless `--purge-data`; typed-name confirmation (or `--yes`); users stay, memberships go

### CR-Q4 Editable group names vs the name pattern (follow-up)
[Answer]: Editable within the pattern `role-<token>-(owner|developer|analyst|writer)`

### CR-Q5 Catalogs (follow-up)
[Answer]: Shared environment catalogs only; listed in the file, anything else refused

### CR-Q6 Renames after apply (follow-up)
[Answer]: Refused; names are locked once applied (state file); remove and recreate instead
