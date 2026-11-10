# Code Generation Plan — Unit 1 Foundation

## Plan Authority and Scope

This is the single source of truth for Code Generation in Unit 1. No application or configuration files may be changed until the user explicitly approves this complete plan. The brownfield project remains organized around its existing root Compose file, shell scripts, Spark configuration, and TPCH directories.

Unit 1 implements the Compose/catalog/KDC/storage foundation and the shared catalog/network contracts. It does not implement Unit 2's complete component identity/permission provisioner, Unit 3's final `databaseA`/`databaseB` service-account ETL and Dremio JDBC Space/view creation, Unit 4's Dremio user/source behavior, or Unit 5's JupyterHub sessions. Those consumers are deferred to their owning units.

Hive 3.1.3 EOL and amd64 emulation on the arm64 host are accepted for this local PoC. Hive/PostgreSQL/Spark/Iceberg/Dremio/RustFS compatibility and Hive/RustFS authorization/effective-user outcomes remain unverified gates; generated code must not claim these acceptance results.

## Workspace and Project Context

- **Workspace root**: `/Users/carlosdiogo/code_repo/hive-dremio-rustfs`
- **Project type**: Brownfield, Docker Compose and shell lifecycle scripts.
- **Application/config locations**: workspace root (`docker-compose.yml`, `.env`, `spark/`, `scripts/`, and new `infra/` files).
- **Documentation location**: `aidlc-docs/current/construction/unit-1-foundation/code/` only for generated implementation notes; user-facing operator docs remain in root `README.md`.
- **Build system**: Docker Compose; no application build system found.
- **Automated tests**: Do not create or run tests in this plan. The developer instructions disallow tests unless requested. Manual verification procedures will be prepared in the later Build and Test workflow stage; their execution is not authorized by this plan.

## Unit Context and Story Traceability

### Stories owned by Unit 1

- **US-CAT-01** — Provide Hive Metastore as the Spark/Iceberg catalog and remove active Nessie service/persistence dependencies.
- **US-AUTH-01** — Provide the Hive-owned authorization integration point, preserving its unverified status until RustFS/effective-user behavior is demonstrated.
- **US-DOC-01** — Provide local foundation startup, stop, explicit destructive reset, and prerequisite documentation.

### Dependencies and shared contracts

- Unit 2 consumes service names, realm naming, credentials directory conventions, and the Hive/RustFS initialization order to provision `user_a`, `user_b`, `admin`, and `write-service-account` with component-owned permissions.
- Unit 3 consumes the Hive Thrift endpoint, Hive Iceberg catalog client settings, RustFS bucket/warehouse conventions, and the `write-service-account` credential contract. This unit does not create the final sample databases or views.
- Units 4 and 5 consume the Hive service principal/keytab contract, catalog endpoint, RustFS network endpoint, and readiness boundaries.
- Dremio JDBC/Space behavior and per-user allow/deny outcomes remain feasibility gates owned by later units.

### Expected interfaces

- Compose service DNS: `metastore-db`, `kdc`, `hive-metastore`, and `object-store` (aliases may retain existing names where needed by consumers).
- Hive Metastore Thrift: internal `hive-metastore:9083` endpoint.
- RustFS S3 API: internal `object-store:9000`; bucket `lake`; warehouse prefix `warehouse/`.
- Local runtime secrets: ignored `.runtime/credentials/` directory with consumer-specific read-only mounts.
- Persistent state: separate named volumes for PostgreSQL metadata, KDC realm, RustFS objects, and existing Dremio state.

## Numbered Generation Steps

### Plan Checklist

- [x] Step 1 — Add local runtime-secret and ignore structure.
- [x] Step 2 — Create the project-owned MIT Kerberos KDC image and configuration.
- [x] Step 3 — Add PostgreSQL and Hive Metastore configuration.
- [x] Step 4 — Make the bucket initializer deterministic and ensure-only.
- [x] Step 5 — Rebuild the Compose foundation and retire Nessie services.
- [x] Step 6 — Define the Spark-to-Hive catalog contract without implementing Unit 3 ETL.
- [x] Step 7 — Retire Nessie-only helper paths.
- [x] Step 8 — Update lifecycle commands and operator documentation.
- [x] Step 9 — Record Unit 1 generated-code summary and limitations.

### Step 1 — Add local runtime-secret and ignore structure

- Create root `.gitignore` rules for `.runtime/`, local `.env`, keytabs, generated credentials, and local logs.
- Create a non-secret `.env.example` with loopback host ports and non-secret configuration only.
- Add a local bootstrap helper under `scripts/` that creates `.runtime/credentials/` with restrictive permissions and generates disposable local secrets without printing them. It must be idempotent and must not overwrite existing credentials silently.
- Keep generated credentials out of tracked/default configuration. Remove remaining inline RustFS credential values from Spark and README in Steps 6 and 8, respectively.
- Traceability: US-DOC-01; NFR-09 through NFR-14; infrastructure design credential boundary.

### Step 2 — Create the project-owned MIT Kerberos KDC image and configuration

- Create `infra/kerberos/Dockerfile` using the approved pinned Debian Bookworm base and pinned MIT Kerberos packages, with an arm64 build target.
- Create KDC/realm configuration under `infra/kerberos/` and a startup/health contract that does not expose the KDC administrative port on the host.
- Add a repeatable foundation bootstrap mechanism for the realm and Hive Metastore service principal/keytab only. Unit 2 owns test-user, platform-admin, and writer provisioning.
- Persist the KDC database in its own named volume; deliver generated keytabs in `.runtime/credentials/` and mount them read-only to consumers.
- Traceability: US-CAT-01, US-DOC-01; infrastructure KDC and credential design.

### Step 3 — Add PostgreSQL and Hive Metastore configuration

- Create `infra/hive/metastore-site.xml` (or the Hive 3.1.3-supported config equivalent) for the external PostgreSQL database, standalone Thrift service, Kerberos/SASL service identity, warehouse location, and explicit authorization-candidate settings only where Hive 3.1.3 semantics are verified.
- Create a one-shot schema initializer using the matching Hive 3.1.3 schema tool. Inspect existing schema first; initialize only an empty metastore database; fail on incompatible state; never auto-upgrade/drop existing state.
- Create a dedicated PostgreSQL database and user with generated local credentials and a separate named data volume. Use a PostgreSQL password file mount where the official entrypoint supports it.
- Configure the Metastore health contract and internal Thrift endpoint. Keep schema verification enabled after initialization.
- Preserve PostgreSQL 16.14 and Hive 3.1.3 as candidates only; do not claim compatibility before later integration verification.
- Traceability: US-CAT-01, US-AUTH-01; infrastructure schema/readiness design.

### Step 4 — Make the bucket initializer deterministic and ensure-only

- Replace inline runtime `pip install` and embedded Python in `docker-compose.yml` with a small initializer under `infra/bucket-init/` and a pinned Boto3 dependency.
- Wait for RustFS readiness; create `lake` only when absent; preserve all existing objects; fail on any error other than the explicit already-exists condition.
- Use a bucket/setup credential distinct from the ETL writer where RustFS supports the required least-privilege policy. If policy behavior cannot be verified, document the limitation without granting an unbounded credential silently.
- Traceability: US-CAT-01, US-DOC-01; NFR-18 through NFR-21.

### Step 5 — Rebuild the Compose foundation and retire Nessie services

- Modify existing `docker-compose.yml` in place: replace `nessie`/`nessie-db` with `kdc`, `metastore-db`, `hive-schema-init`, and `hive-metastore`; retain Dremio, Spark, and RustFS services in their approved unit boundaries.
- Remove the active Nessie catalog and database services, Nessie-only volumes, and Nessie service dependencies. Keep dependent workload services out of the default foundation startup until Unit 3 replaces their Nessie-specific behavior.
- Define separate named volumes, the private Compose network, healthchecks, and `service_healthy`/`service_completed_successfully` gates. Preserve state on normal stop and failure.
- Bind all developer-facing host ports explicitly to `127.0.0.1`. Keep PostgreSQL, Hive Thrift, and KDC/Kadmin internal unless a reviewed local tool requires loopback publication.
- Preserve existing RustFS, Dremio, and Spark image pins where compatible. Resolve immutable image digests during implementation. Do not silently bump service versions.
- Traceability: US-CAT-01, US-AUTH-01, US-DOC-01; all approved NFR Design patterns.

### Step 6 — Define the Spark-to-Hive catalog contract without implementing Unit 3 ETL

- Update existing `spark/spark-defaults.conf` in place to remove Nessie catalog settings and define the approved Hive-backed Iceberg catalog, internal Metastore endpoint, Kerberos client settings, and RustFS endpoint/path-style settings.
- Remove hard-coded S3 credentials; consume runtime credentials through the Unit 2/3 secret contract.
- Do not change `tpch/load_tpch.py` table/database behavior or create `databaseA`/`databaseB` in this unit. Unit 3 owns writer-based ETL, sample tables, and Dremio JDBC objects.
- Ensure the default Compose foundation does not start the current Nessie-dependent TPCH loader. Defer its replacement to Unit 3; no default startup path may attempt to contact a removed Nessie service.
- Traceability: US-CAT-01 and Unit 3 integration interfaces.

### Step 7 — Retire Nessie-only helper paths

- Remove `spark/test-nessie.py` and the Nessie-specific `tpch/register_missing.py` helper when they are no longer referenced by the foundation topology. Do not replace them with incomplete Hive registration behavior; Unit 3 owns the replacement workload flow.
- Preserve `spark/seed.py` only if inspection confirms it is an independent Hadoop-catalog example and is not included in the default runtime path; otherwise document its status clearly.
- Traceability: US-CAT-01; no-active-Nessie-runtime-path requirement.

### Step 8 — Update lifecycle commands and operator documentation

- Modify `scripts/start.sh` to validate local runtime inputs, start the approved foundations in dependency order, display loopback URLs, and report readiness/failure without exposing secrets.
- Add `scripts/stop.sh` for non-destructive container stop/down behavior that preserves volumes.
- Modify `scripts/clean.sh` to make full reset explicit and clearly destructive, require an unmistakable confirmation token, and remove named volumes only after confirmation.
- Rewrite root `README.md` for Hive/Kerberos/RustFS local setup, image architecture limitation, credential generation, service status/logging, stop versus reset, and unresolved authorization/version gates. Remove Nessie source/setup instructions.
- Traceability: US-DOC-01; NFR-23 through NFR-26.

### Step 9 — Record Unit 1 generated-code summary and limitations

- Create `aidlc-docs/current/construction/unit-1-foundation/code/implementation-summary.md` listing created/modified/retired files, service interfaces, credential handling, dependency ordering, and open compatibility/authorization gates.
- Check that every Code Generation plan step has a corresponding output and that no duplicate files were introduced.
- Do not add or execute automated tests. Record any static/manual inspection only; manual runtime verification instructions belong to the later Build and Test workflow stage.
- Traceability: all Unit 1 stories and implementation plan reviewability.

## Explicit Exclusions for This Unit

- No Unit 2 creation of `admin`, `write-service-account`, `user_a`, or `user_b` component accounts/permissions, except a minimal Hive Metastore service identity required to start the service.
- No Unit 3 TPCH ETL redesign, sample database/table creation, Dremio Space/view creation, or Dremio JDBC writer implementation.
- No Unit 4 Dremio source/user/impersonation setup, and no Unit 5 JupyterHub/Spark-user-session configuration.
- No Airflow/Jenkins changes, cloud deployment, production KDC, monitoring stack, message broker, HA, or LAN exposure.
- No test files or test execution.

## Approval Status

Plan approved by user on 2026-10-23. All nine generation steps are complete and the generated artifacts are awaiting user review.
