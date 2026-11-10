# Unit 2 Identity and Permission Provisioning — Infrastructure Design

## Scope and Deployment Target

Implement identity provisioning as an explicitly invoked, one-shot Compose operation inside the existing local project. It uses the private Compose network to reach component-owned setup interfaces and the ignored host `.runtime/credentials/` tree for protected credential inputs/outputs. It is not included in default `docker compose up`, has no published ports, and does not retain an identity database or persistent service process.

Unit 2 provisions Kerberos principals and component-native admin/writer accounts, plus storage credentials needed by later user sessions. Unit 3 creates sample databases and tables as `write-service-account`; Unit 4 configures Dremio's Hive source and query-user mapping; Unit 5 configures JupyterHub user sessions. Airflow/Jenkins remain out of scope.

### User Clarification — Dremio Local Accounts

The user approved manual creation of Dremio local accounts. The operator creates `admin` during Dremio first-run and creates `write-service-account` in the UI using the protected credentials under `.runtime/credentials/`. The one-shot provisioner does not call an undocumented password API. The writer must not receive the `ADMIN` role. This supersedes the earlier plan for an automated Dremio user adapter.

## Service and Image Mapping

| Logical service/component | Infrastructure design | Readiness / state |
|---|---|---|
| Existing `kdc` | Retain the Unit 1 MIT KDC container and realm volume. Extend the supported local admin ACL for the `admin@LAKEHOUSE.LOCAL` platform principal while keeping bootstrap control separate. Create distinct principals/keytabs for `admin`, `write-service-account`, `user_a`, and `user_b`. | KDC healthcheck must pass before provisioning. Existing `hive/hive-metastore` principal/keytab is preserved. KDC database remains in its existing named volume; keytabs remain in the host runtime credential directory. |
| New `identity-provisioner` one-shot service | Project-owned, locally built image containing only the client tooling/adapters needed for supported KDC, PostgreSQL, RustFS, Dremio, and Hive setup interfaces. Place it behind an explicit `identity-provisioning` Compose profile and invoke only after core services and Dremio's first local-admin setup are ready. Use `--rm`; no host ports. Exact runtime/base pin and tooling are selected in Code Generation after interface validation. | Depends on KDC, metastore PostgreSQL, Hive Metastore, RustFS, and successful bucket initialization. Dremio must be running and its first-run local admin initialized; its account adapter performs an authenticated preflight and fails with a prerequisite message if setup is incomplete. |
| Credential input/output boundary | Keep files in `.runtime/credentials/` (ignored and host-restricted). Mount only each adapter's component-specific admin/setup credential read-only. Bind a restricted output directory for generated keytabs and native user credentials; create files with owner-only access. | No secrets in environment dumps, command arguments, image layers, logs, or the provisioner's writable image filesystem. The provisioner reports references/status only. Exact filenames and host UID/GID handling are Code Generation details. |
| RustFS account/policy adapter | Use the pinned RustFS native IAM management interface with the existing root/setup credential only for bootstrap. Create separately keyed named identities and policies for platform admin, writer, and later test-user Spark access. Keep root setup credentials confined to object-store and provisioning/setup paths; do not pass them to Spark. | RustFS and `lake` bucket must be ready. RustFS documentation describes root, IAM user, service-account, and policy attachment models; this documentation is current, so availability and API behavior must be checked against pinned `1.0.0-glibc` before claiming support. [RustFS IAM](https://docs.rustfs.com/en/security-compliance/iam), [RustFS credentials](https://docs.rustfs.com/en/operations/credentials). |
| Dremio account adapter | Use Dremio Community's supported local-user management interface to ensure an `admin` user and a separate `write-service-account` local user after first-run initialization. Keep component passwords separate. Do not grant writer the `ADMIN` role. | Dremio 26 Community supports local identities according to the current editions documentation. Exact API payload, idempotence, and password handling must be validated against the pinned `26.0.5` image. Hive-source setup and JDBC Space-write feasibility are Unit 4 gates. [Dremio editions](https://docs.dremio.com/editions/), [Dremio user management](https://docs.dremio.com/current/security/authentication/users). |
| PostgreSQL roles | Ensure a native PostgreSQL `admin` role with a credential distinct from the Hive service credential. Preserve the metastore database and schema; reduce the Hive service account to the rights needed by Hive after confirming schema ownership and startup behavior. | Current Compose sets `POSTGRES_USER=hive`. The official image creates the configured `POSTGRES_USER` with superuser power on fresh initialization, so the persisted role must be inspected and migrated in place. Initialization scripts only run for an empty data directory; do not rely on a restart to apply a role migration. Use an idempotent one-shot migration that preserves the existing volume and stops if post-migration Hive checks fail. [Official Postgres image behavior](https://github.com/docker-library/docs/blob/master/postgres/README.md?plain=1). |
| Hive/Hadoop authorization adapter | Keep standalone Hive Metastore and the existing Kerberos SASL service. Provision the `admin` Kerberos identity and writer/read grant requests only through a Hive-owned supported mechanism. Do not add HiveServer2 or a policy service in this infrastructure baseline. | The current Hive template has SASL, Kerberos, and `hive.metastore.execute.setugi=true`; these settings do not prove DDL authorization or effective-user checks against S3A/RustFS. Writer grants and post-ETL reader grants remain blocked on exact-version validation. |
| Spark and Jupyter consumers | Remove the current shared RustFS `env_file` from the long-running Spark service so it does not inherit RustFS root credentials. Unit 3 injects only writer credentials into its ETL invocation; Unit 5 supplies distinct read credentials to isolated user sessions. | Spark is a credential consumer, not an account database. JupyterHub admin and user-session mapping are implemented with Unit 5. |

## Identity and Permission Mapping

| Identity / component | Native infrastructure action | Access boundary / owner |
|---|---|---|
| Kerberos `admin` | Create principal and separate keytab; grant only local KDC administration capability through the KDC ACL. | KDC owns principal and ACL. Bootstrap/master credential remains separate. |
| Kerberos `write-service-account` | Create principal and separate keytab. | KDC owns principal; Spark consumes in Unit 3. |
| Kerberos `user_a`, `user_b` | Create separate principals and keytabs. | KDC owns identities; per-user Spark sessions consume in Unit 5. |
| RustFS `admin` | Create a named native administrator identity/policy, distinct from RustFS root/setup credentials. | RustFS owns the IAM identity and policy; validate pinned-version behavior. |
| RustFS `write-service-account` | Create a distinct access key and policy restricted to the writer's warehouse prefixes for `databaseA` and `databaseB`. | RustFS owns S3 permission evaluation. Exact supported prefix semantics must be tested. |
| RustFS `user_a`, `user_b` | Create distinct credentials/policies limited to their eventual data paths. | RustFS owns storage policy; align with Unit 3 database locations and Unit 5 sessions. Direct S3 access is not a user acceptance scenario. |
| Dremio `admin` | Use the initialized local administrator identity created during first-run setup; store its credential separately. | Dremio owns local identity and administrator role. |
| Dremio `write-service-account` | Ensure a separate local user via supported interface; do not add to administrator role. | Dremio owns user and Space privileges. Non-admin object creation over JDBC is a Unit 4 feasibility gate. |
| PostgreSQL `admin` | Ensure a separate native administration role using its own credential. | PostgreSQL owns role. Preserve current metadata; service role remains `hive` and gets no unnecessary superuser privileges after migration. |
| Hive `admin` | Use the Kerberos `admin` principal for authenticated Metastore access; storage/path administration behavior must be determined by the selected Hive authorization model. | Hive Metastore has no general local-user database. Do not claim admin authorization merely because SASL authentication succeeds. |
| Spark/Jupyter `admin` | Provide an operator-use Kerberos keytab and local runtime access procedure; map JupyterHub administrator status in Unit 5. | Spark has no built-in account store. JupyterHub is not yet present in Unit 2. |

## PostgreSQL Role Migration Constraint

The active Compose configuration currently uses `POSTGRES_USER=hive`. Per the official PostgreSQL image behavior, a fresh volume receives that configured role as a superuser. This is broader than the desired Hive service identity and prevents the admin/service-account separation from being considered complete.

Code Generation must therefore implement and verify a non-destructive role transition: create a distinct PostgreSQL `admin` credential/role; preserve the current Hive metastore database, schema, and owner requirements; then remove unnecessary superuser capability from `hive` while retaining the minimum rights required by Hive and `schematool`. Validate against the existing persistent volume as well as a fresh initialization. If Hive cannot operate with the restricted service role, stop and report the required privilege instead of deleting/recreating the volume.

## RustFS Root-Credential Containment

The current Compose file gives `.runtime/credentials/rustfs.env` to RustFS, the bucket initializer, Hive Metastore, and Spark. Unit 2's integration must remove that shared root credential from Spark and use named per-identity credentials for all Spark jobs/sessions. Root/setup access remains limited to provisioning and the specific setup components that require it. Hive Metastore's continued use of a storage-level setup credential is a separate compatibility/authorization gate; do not describe `setugi` as proving S3 enforcement.

## Network and Exposure

- Attach the provisioner to the existing private `iceberg_net` network.
- Publish no provisioner, PostgreSQL, Hive, or KDC ports to the host. Existing developer-facing service ports remain bound to `127.0.0.1`.
- Access KDC admin, PostgreSQL, RustFS admin, and Dremio APIs through internal Compose service names.
- Keep the existing service-to-service topology; no gateway, external identity provider, queue, shared network, or LAN access is added.

## Readiness and Provisioning Order

1. `scripts/start.sh` initializes the existing KDC service identity, PostgreSQL Hive schema, RustFS bucket, Hive Metastore, Spark, and Dremio as it does for Unit 1.
2. The operator completes Dremio's initial local administrator setup through the UI once and stores the credential in protected runtime storage. Provisioning must not guess or automate this first-run state.
3. The operator explicitly invokes the identity-provisioner profile. Preflight checks KDC health, PostgreSQL availability/schema, RustFS readiness/bucket, Hive Thrift readiness, Dremio authenticated readiness, and required files before mutation.
4. Provision sequentially: KDC principals/keytabs; RustFS named accounts/policies; PostgreSQL native admin role and safe Hive-role restriction; Dremio writer account; Hive writer capability only if the supported mechanism is verified. Component adapters report independent outcomes.
5. On failure, stop at the required failing operation, preserve all prior state, redact diagnostics, and return nonzero/incomplete. Do not mark ETL ready.
6. Unit 3 runs sample ETL as `write-service-account`. After its databases exist, the separate post-ETL phase attempts reader grants and reports configured versus blocked state.

## Persistence and Lifecycle

- KDC database, PostgreSQL metastore data, RustFS objects, and Dremio state stay in their existing named volumes.
- Generated credentials and keytabs remain in `.runtime/credentials/` and survive ordinary stop/start. The provisioner container is removed after the one-shot run; it owns no persistent data volume.
- Normal reruns ensure accounts and preserve credential values. Explicit rotation updates only the owning component and dependent credential file, with documented consumer restart order.
- Full reset remains the existing explicit destructive operation. Identity setup failure never invokes it.

## Category Decisions

- **Messaging**: Not applicable; setup is synchronous and sequential.
- **Monitoring**: No added service; use Compose health/status and secret-safe logs.
- **Shared infrastructure**: Not applicable; local single-project PoC only.
- **Compute scaling**: One temporary provisioner execution; no replicas or concurrent provisioning.

## Open Compatibility and Security Gates

1. Validate RustFS IAM user/policy support and least-privilege prefixes against the exact pinned `1.0.0-glibc` image; current RustFS documentation describes IAM and policy attachment but is not version-specific to this image.
2. Validate Dremio Community `26.0.5` local-user creation and safe idempotent password handling. Official documentation lists local identities for Community 26.0+, but does not alone prove the exact automation path or non-admin Space write permission.
3. Validate whether Hive's standalone Metastore plus S3A/RustFS can enforce writer and reader permissions across Spark and Dremio. Existing Kerberos/setugi properties do not prove that behavior.
4. Validate the PostgreSQL role migration and confirm Hive schema operations still work after restricting `hive`; test both existing and fresh database volumes without deleting state.
5. Complete `admin` component mappings for Hive and JupyterHub without claiming a native user store where none exists. JupyterHub configuration remains Unit 5.
6. Confirm credential mounts/permissions work on the host's Docker environment and that logs/process inspection do not expose secret contents.

If a gate fails, present evidence and the smallest change for user review before changing versions, adding services, or broadening permissions.
