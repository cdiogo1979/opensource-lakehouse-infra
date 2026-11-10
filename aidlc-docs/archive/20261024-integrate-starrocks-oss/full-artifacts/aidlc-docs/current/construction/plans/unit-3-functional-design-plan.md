# Unit 3 Functional Design Plan — SQL Bootstrap and Catalog Access

## Unit Context

- **Unit:** Unit 3 — SQL Bootstrap and Catalog Access.
- **Stories:** US-01 query existing Iceberg data; US-02 write Iceberg data as the ETL identity; US-03 enforce SQL authorization; US-04 use dedicated service credentials.
- **Requirements:** FR-2, FR-3, FR-6, NFR-1, NFR-2, and FR-7 preservation constraints.
- **Dependencies:** Unit 1 StarRocks Kerberos/RustFS identities and Unit 2 FE/BE runtime.
- **Completion boundary:** An idempotent bootstrap configures a StarRocks Iceberg external catalog backed by the secured Hive Metastore and RustFS, then applies the approved SQL account/access matrix. Query, write, and compatibility acceptance remain for Build and Test.
- **Canonical design ownership:** `aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/starrocks-analytics.md` and `lakehouse-workload-and-access.md`.

## Approved Functional Baseline

- The catalog is StarRocks `type = iceberg` with `iceberg.catalog.type = hive`, using the existing Hive Metastore Thrift endpoint and RustFS S3-compatible endpoint. StarRocks documents Iceberg as a distinct catalog type and supports HMS-backed Iceberg tables, including reads and writes; S3-compatible configuration uses endpoint, path-style access, and dedicated credentials. See the [StarRocks Iceberg catalog guide](https://docs.starrocks.io/docs/data_source/catalog/iceberg/).
- The service uses the Unit 1 `starrocks@<realm>` Kerberos principal/keytab for Hive Metastore access and the `starrocks` RustFS account for object access. StarRocks SQL identities remain distinct from these service credentials.
- The SQL access matrix is fixed by approved requirements:

  | SQL identity | `databaseA` | `databaseB` |
  |---|---|---|
  | `user_a` | Read | Deny |
  | `user_b` | Read | Read |
  | `write_service_account` | Read and write | Read and write |
  | `admin` | Full StarRocks access | Full StarRocks access |

- The `write-service-account` Kerberos/RustFS identity maps to StarRocks SQL user `write_service_account` if required by naming rules.
- The bootstrap is repeatable and must preserve existing Hive databases/tables/objects and existing SQL password files. It must not implicitly rotate credentials or drop/recreate the catalog, users, roles, databases, or tables.
- Selected bootstrap behavior: secure built-in `root` with its own generated, persisted password, create `admin` with a distinct password, and use the protected root credential for reruns.
- Selected writer scope: DML writes to existing tables only. Creating, altering, or dropping databases/tables is excluded, as is StarRocks administration.
- Selected credential lifecycle: generate per-identity password files only when absent, preserve existing files unchanged, never print values, and fail closed if an existing SQL account does not authenticate with its protected file.
- Selected existing-state behavior: inspect and add only known-safe missing catalog settings/grants; preserve unrelated grants and objects; fail with a redacted diagnostic on conflicting or broader target state.

## Functional Design Tasks

- [x] **Step 1 — Analyze unit context:** Review approved requirements, stories, Unit 1 identity handoff, Unit 2 runtime, existing Iceberg/HMS/S3 configuration, and shared access design.
- [x] **Step 2 — Define fixed baseline:** Capture catalog type, endpoints, service identity boundary, SQL access matrix, and data-preservation rules.
- [x] **Step 3 — Resolve bootstrap and grant questions:** All four questions answered; resolutions are recorded below and reflected in the design.
- [x] **Step 4 — Generate functional design:** Created the business logic model, business rules, and domain entities under `aidlc-docs/current/construction/unit-3-starrocks-sql-bootstrap/functional-design/`.
- [x] **Step 5 — Validate and present:** Reviewed design traceability to FR-2/3/6, NFR-1/2, US-01 through US-04, and preservation requirements. Artifacts are ready for user review; no implementation or runtime verification is claimed.
- [x] **Step 6 — Record approval:** User approved Functional Design and continued to Unit 3 NFR Requirements on 2026-10-24.

## Questions

Fill each `[Answer]:` line with an option letter. Choose the last option, `Other`, and describe your choice if none fits.

### Question 1 — Secure the built-in StarRocks bootstrap account

StarRocks FE initially exposes the built-in `root` SQL account without a password. How should Unit 3 handle it while creating the requested `admin` account?

A) Generate and persist a separate protected root password, set it during the first bootstrap, use it on subsequent reruns, and create `admin` with its own protected password.

B) Keep `root` passwordless and use it only through the local FE container; create the separately password-protected `admin` account.

C) Require the operator to secure the built-in root account and place its password in the protected credential file before running Unit 3 bootstrap.

D) Other (describe below).

[Answer]: A — use a generated, separately protected root password for initial bootstrap and reruns; create `admin` with its own protected password.

### Question 2 — Writer DDL authority

The writer must read/write Iceberg data in both existing databases and must not administer StarRocks. Which object-creation scope should it receive?

A) Allow DML writes to existing tables only; deny creating, altering, and dropping databases/tables.

B) Allow creating and altering tables in `databaseA` and `databaseB`, plus DML writes; deny database creation/drop, table drop, user/role management, and global administration.

C) Allow creating, altering, and dropping tables in both databases plus DML writes; deny database and StarRocks administration.

D) Other (describe below).

[Answer]: A — allow DML writes only to existing tables in `databaseA` and `databaseB`; deny database/table DDL and administration.

### Question 3 — Generated SQL password files

Requirements call for generated passwords persisted under the protected local credential convention. Which lifecycle should the bootstrap implement?

A) Generate one password file per SQL identity when absent, preserve existing files unchanged, fail closed on existing-account/password drift, and never print values.

B) Generate per-identity files when absent and reconcile existing SQL passwords from those files on each run, without regenerating file contents.

C) Require each password file to be created manually before bootstrap; the bootstrap fails if a file is missing and never generates passwords.

D) Other (describe below).

[Answer]: A — generate each SQL password file when absent, preserve it unchanged, fail closed on account/password drift, and never print secrets.

### Question 4 — Catalog setup and existing state

If the target catalog or SQL users/roles already exist when bootstrap runs, what should happen?

A) Inspect and reconcile only known-safe missing settings/grants; preserve unrelated grants and objects; fail with a redacted diagnostic for conflicting or broader state.

B) Require a pristine StarRocks FE state and fail if any target catalog/user/role exists.

C) Reconcile the script-owned catalog properties and target role grants to the desired state, while preserving unrelated grants and all data objects.

D) Other (describe below).

[Answer]: A — inspect existing state, reconcile only known-safe missing settings/grants, preserve unrelated state, and fail with a redacted diagnostic on conflicts or broader access.

## Design Review Status

- **Artifacts ready:** `functional-design/business-logic-model.md`, `functional-design/business-rules.md`, and `functional-design/domain-entities.md`.
- **Important scope decision:** `write_service_account` is a DML writer for existing tables; it does not create, alter, or drop tables or databases.
- **Approval gate:** Approved by the user on 2026-10-24; Unit 3 NFR Requirements is now active.
- **Verification boundary:** No application code, SQL bootstrap, test, image build, service lifecycle action, or data operation was performed as part of this functional design.

## Applicability Notes

- Frontend/UI design is not applicable; operations use SQL bootstrap and command-line tooling.
- Passwords/keytabs and RustFS secret values remain protected runtime inputs, never tracked or logged.
- Security Baseline is disabled; the explicit least-privilege and credential requirements above remain mandatory. Property-Based Testing is partial and applies only if pure functions/serialization are introduced. No application code, SQL bootstrap, builds, or tests are created in this planning stage.
- Build and Test must separately verify secured HMS access, Iceberg table compatibility, S3 access, reads/writes, all allowed/denied SQL grants, repeatability, and preservation of current data.
