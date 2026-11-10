# Code Generation Plan — Unit 2 Identity and Permission Provisioning

## Plan Authority and Scope

This is the single source of truth for Unit 2 Code Generation. No application or configuration files may be changed until the user approves this complete plan. Unit 2 implements the approved one-shot identity provisioner and component-owned account setup while preserving existing state.

Unit 2 provisions `admin`, `write-service-account`, `user_a`, and `user_b` in Kerberos; native admin/writer accounts in RustFS and PostgreSQL; required RustFS service/user credentials; and the initial writer permission setup only where a supported Hive-owned mechanism can be verified. Per the user's clarification, Dremio's first-run `admin` and `write-service-account` local accounts are created manually in the UI with their protected local credential files. Unit 2 does not create sample databases/tables, build Dremio's Hive source, configure JupyterHub sessions, or change Airflow/Jenkins. Those remain later units or deferred scope.

The approved design requires component-specific credentials, no writer administrator access, a safe in-place PostgreSQL role migration, removal of RustFS root credentials from Spark, and explicit reporting of unsupported API/authorization behavior. Hive/RustFS effective-user enforcement and Dremio non-admin Space writes remain unverified feasibility gates.

## Workspace and Project Context

- **Workspace root**: `/Users/carlosdiogo/code_repo/hive-dremio-rustfs`
- **Project type**: Brownfield Docker Compose PoC; services currently run locally.
- **Application/configuration paths**: `docker-compose.yml`, `infra/`, `scripts/`, `spark/`, local ignored `.runtime/credentials/`.
- **Documentation paths**: `aidlc-docs/current/` for workflow records; root `README.md` for operator instructions.
- **Existing runtime contracts**: realm `LAKEHOUSE.LOCAL`; KDC `kdc`; Hive Metastore `hive-metastore:9083`; PostgreSQL `metastore-db:5432`; RustFS `object-store:9000`; Dremio local UI/API; bucket `lake`; warehouse `s3a://lake/warehouse/`.
- **Current implementation findings**:
  - `POSTGRES_USER=hive` means the official image initializes that role as a superuser on a fresh data directory. The existing metadata volume must be migrated in place; do not reset it.
  - `.runtime/credentials/rustfs.env` is currently passed to Spark, Hive Metastore, the bucket initializer, and RustFS. It contains root/setup credentials. Spark must stop receiving those credentials; Hive Metastore must receive a separate native service identity if the pinned RustFS/Hive integration supports it.
  - The KDC ACL currently names `kadmin/admin@LAKEHOUSE.LOCAL`, but Unit 1 only created the Hive service principal. A protected bootstrap KDC administration credential/interface is needed for remote one-shot provisioning.

## Authorized Design Inputs

- Approved Unit 2 Functional Design artifacts under `construction/unit-2-identity/functional-design/`.
- Approved Unit 2 NFR Requirements under `construction/unit-2-identity/nfr-requirements/`.
- Approved Unit 2 NFR Design under `construction/unit-2-identity/nfr-design/`.
- Approved Unit 2 Infrastructure Design under `construction/unit-2-identity/infrastructure-design/`.
- Approved requirements and Unit 1 runtime contracts.

## Generation Steps

### Plan Checklist

- [x] Step 1 — Extend protected local credential bootstrap for Unit 2 identities without overwriting current credentials.
- [x] Step 2 — Add a protected KDC provisioning bootstrap and final user/admin principals/keytabs.
- [x] Step 3 — Add the explicit one-shot identity-provisioner image, adapters, and Compose profile. Dremio account setup is a manual prerequisite per user clarification.
- [x] Step 4 — Add RustFS named IAM users/policies and separate Hive service/writer/test-user credentials. Runtime behavior remains a Build and Test gate.
- [x] Step 5 — Document manual Dremio local admin/writer account setup after operator first-run initialization, using the protected credential files. (User approved manual account creation.)
- [x] Step 6 — Add non-destructive PostgreSQL admin/service-role separation; runtime verification follows in Build and Test.
- [x] Step 7 — Remove shared RustFS root credentials from Spark and configure named Hive service credentials after successful provisioning. Runtime behavior remains a Build and Test gate.
- [x] Step 8 — Update operator instructions and startup/status messages without provisioning identities implicitly.
- [x] Step 9 — Record implementation summary, file inventory, and unresolved feasibility gates.

### Step 1 — Extend protected local credential bootstrap

- Extend `scripts/bootstrap-local.sh` to create missing component-native administrator and writer credentials, a RustFS KDC-provisioning bootstrap credential reference as required, and a restricted output directory for generated keytabs/users.
- Preserve existing `.runtime/credentials/` values. Do not print, rotate, or overwrite existing credentials implicitly.
- Keep the existing RustFS root credential distinct from RustFS named IAM identities. Add no real secrets to tracked files or `.env`.
- Set directory/file modes explicitly and avoid shell tracing or command arguments that reveal values.
- Traceability: US-ID-01/02; U2-NFR-10–14, U2-NFR-28.

### Step 2 — Extend Kerberos administration bootstrap

- Modify `infra/kerberos/entrypoint.sh` and `infra/kerberos/kadm5.acl` to establish a protected, local provisioning credential for remote `kadmin` operations and grant the final `admin@REALM` principal the approved local KDC administration capability.
- Add `admin`, `write-service-account`, `user_a`, and `user_b` as distinct principals and export separate keytabs to `.runtime/credentials/keytabs/`; preserve `hive/hive-metastore` and its keytab.
- Keep the provisioning credential separate from the final `admin` user and accessible only to the KDC/provisioning workflow. Do not mount the Docker socket into the provisioner.
- Make KDC bootstrap and keytab export idempotent, avoid key rotation on rerun, and redact principal-management secret material.
- Traceability: US-ID-01/02; FR-06/07/19; U2-NFR-07–13.

### Step 3 — Add the one-shot identity provisioner

- Add a project-owned `infra/identity-provisioner/` image and implementation with small component-specific adapters for KDC, RustFS, PostgreSQL, Dremio, and Hive.
- Use a local-only runtime with pinned base/tool dependencies selected after confirming exact API/CLI requirements. No service stays running after the provisioning operation.
- Add an `identity-provisioning` Compose profile for the explicit one-shot service. Keep it out of default `docker compose up`; publish no ports; attach only to `iceberg_net`; use `--rm` for invocation.
- Gate on KDC, PostgreSQL/schema, Hive, RustFS/bucket, and Dremio availability. Require authenticated Dremio first-run setup as an operator prerequisite. Preflight all dependencies and required credential files before mutation.
- Process identities sequentially. Report `created`, `already-present`, `deferred`, or `failed` per component/identity. Stop at the first required failure, preserve prior setup, redact output, and return nonzero/incomplete.
- Traceability: US-ID-01/02; U2-NFR-21–30.

### Step 4 — Add RustFS native identities and scoped policies

- Use the RustFS root/setup key only for the administrative bootstrap operation. Create distinct RustFS `admin`, `write-service-account`, `user_a`, `user_b`, and Hive Metastore service identities with separately generated key pairs, where supported by the pinned image.
- Define writer policy resources for only the required `lake/warehouse/databaseA` and `databaseB` paths; align test-user policy paths with their approved read profiles; keep a distinct Hive service policy if Hive needs direct S3A access.
- Do not rely on current upstream docs alone to prove that RustFS 1.0.0-glibc implements IAM/prefix behavior. The generated adapter uses the documented SigV4 admin interface; Build and Test must verify actual responses and permission outcomes against the pinned image. If unsupported, stop and document the smallest adjustment; do not grant whole-bucket access silently.
- Do not pass root credentials to Spark or user sessions.
- Traceability: FR-17/18/23; US-ID-01; U2-NFR-10–20.

### Step 5 — Document manual Dremio local admin/writer account setup

- Assume the operator completes first-run Dremio local admin creation through the UI and stores the password in protected local credentials.
- Document that the operator creates the `admin` local administrator during Dremio first-run using `.runtime/credentials/dremio-admin-password`, then creates `write-service-account` as a local user using `.runtime/credentials/dremio-writer-password`.
- Keep the writer out of the `ADMIN` role. Preserve existing credentials unless explicit rotation is requested. Do not attempt account creation through an undocumented API.
- Do not configure the Hive source, query identity mapping, Spaces/views, or JDBC writer permissions here; Unit 4 owns these.
- Traceability: FR-20–22; US-ID-02/US-JDBC-01; U2-NFR-17–20.

### Step 6 — Separate PostgreSQL admin and Hive service roles

- Add a non-destructive idempotent PostgreSQL role migration invoked by the one-shot provisioner. Create a separate `admin` role/credential and ensure the Hive service role retains only required metastore database/schema privileges.
- On the existing initialized volume, inspect role state first; create the new administrator before revoking unnecessary privileges from `hive`. Do not change database ownership or schema privileges blindly.
- Build and Test must exercise Hive Metastore and matching `schematool` operations after migration. Preserve the PostgreSQL named volume and stop with a redacted error if the service role cannot operate under the intended privileges.
- Ensure fresh initialization and existing-volume migration both reach the same role contract. Never rely only on `/docker-entrypoint-initdb.d/` for an existing data directory.
- Traceability: FR-20; US-ID-02; U2-NFR-07–09, U2-NFR-10/12, U2-NFR-21–25.

### Step 7 — Isolate RustFS credentials in runtime consumers

- Remove `.runtime/credentials/rustfs.env` from the long-running Spark service so Spark no longer receives RustFS root credentials.
- Update Hive configuration rendering and service mounts to use a named Hive Metastore service credential only if the account/policy and Hive S3A behavior are supported by the pinned versions. Otherwise document the minimum blocking requirement; never silently preserve root credential exposure as a successful least-privilege result.
- Keep bucket initializer setup credentials separate from writer credentials, scoped as supported.
- Leave Unit 3 ETL and Unit 5 user-session credential injection to those units; establish credential file names and mount contracts they can consume.
- Traceability: FR-18/23; US-ID-01; U2-NFR-10–15.

### Step 8 — Update operator instructions and startup boundaries

- Modify `README.md` with the manual Dremio first-run prerequisite, explicit provisioning command, credential-file handling, status interpretation, rotation guidance, and safe recovery.
- Keep `scripts/start.sh` focused on core services; do not run identity provisioning automatically. Add only a separate explicit helper if needed to invoke the profile.
- Document that provisioning success is not proof of Hive/RustFS allow/deny behavior, Dremio JDBC Space writes, or user effective identity.
- Document Unit 3's subsequent writer ETL and the post-ETL reader-grant phase.
- Traceability: US-DOC-01; U2-NFR-27–30.

### Step 9 — Record implementation summary and gates

- Add `aidlc-docs/current/construction/unit-2-identity/code/implementation-summary.md` with created/modified files, identity-to-component mapping, secret boundaries, invocation, migration behavior, and unresolved gates.
- Review changes for default startup side effects, root credential exposure, shell/process secret leaks, destructive volume operations, and privilege escalation.
- Do not create or run automated tests as part of Code Generation. Build/runtime verification and test instructions follow in the later Build and Test stage.
- Traceability: all Unit 2 stories and approved design artifacts.

## Explicit Exclusions for Unit 2

- No sample database/table creation, TPC-H ETL, or Dremio Space/view creation.
- No Dremio Hive source configuration, query-user identity mapping, or authorization demonstration.
- No JupyterHub deployment or user-session wiring.
- No Airflow/Jenkins changes, external identity provider, persistent identity service, central policy engine, or monitoring stack.
- No deletion/recreation of KDC, PostgreSQL, RustFS, or Dremio volumes to make provisioning succeed.
- No writer administrator access or blanket whole-bucket policy as a workaround.
- No tests or test execution in this Code Generation plan.

## Evidence and Version Constraints

- Current RustFS documentation describes root and IAM identities and policy attachment; verify those operations against the pinned RustFS 1.0.0-glibc image before relying on them: [RustFS IAM](https://docs.rustfs.com/en/security-compliance/iam).
- Dremio Community 26+ documents local identities; validate the exact 26.0.5 account-management and password interface: [Dremio editions](https://docs.dremio.com/editions/), [Dremio user management](https://docs.dremio.com/current/security/authentication/users).
- The official PostgreSQL image documents `POSTGRES_USER` as a superuser on fresh initialization and notes init scripts run only for an empty data directory: [PostgreSQL image documentation](https://github.com/docker-library/docs/blob/master/postgres/README.md?plain=1).
- Hive Metastore storage-based authorization over S3A/RustFS remains unverified. Do not mark writer/read grants as achieved unless later checks prove them.

## Approval Status

**Approved by the user on 2026-10-23** (“approve and continue”). The user clarified that Dremio local account creation may be manual. Code Generation artifacts are complete; pinned-interface, migration, and authorization verification are Build and Test gates. See `../unit-2-identity/code/implementation-summary.md` for the generated file inventory and limits.
