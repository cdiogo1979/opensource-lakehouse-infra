# Central Identity and Environment Access Requirements

## Intent

Replace the test identities `user_a` and `user_b` with centrally managed `developer-user` and `analyst-user` identities, while retaining `admin` and `write-service-account`. Use FreeIPA as the human and service identity source, and Apache Ranger for supported data authorization. Align RustFS bucket policies, Hive database locations, Spark access, and StarRocks query authorization with the role matrix below.

## Approved storage layout

| Environment | RustFS bucket | Data placement |
|---|---|---|
| Production | `lake` | Existing objects remain in place; production databases use this bucket. |
| Development | `lake-dev` | Development databases, including `lhdev*`, use this bucket. |
| UAT | `lake-uat` | UAT databases use this bucket. |

Bucket names use hyphens because the pinned RustFS S3 API rejects underscores. The production bucket remains `lake`; no data migration is required for this naming correction because the new environment buckets had not been provisioned before validation.

Provisioning must create `lake-dev` and `lake-uat` only when absent and must preserve all existing bucket contents. No automatic data migration or deletion is in scope.

## Identity and role matrix

| Identity | Read | Write | Administration |
|---|---|---|---|
| `developer-user` | All databases and object paths in `lake`, `lake-dev`, and `lake-uat` | `lake-dev` only | None |
| `analyst-user` | Production databases and object paths in `lake` only | None | None |
| `write-service-account` | All databases and object paths in all three buckets | All databases and object paths in all three buckets | None |
| `admin` | All | All | Retain existing platform administration role |

Access control must be enforced at the object-storage and SQL/query layers, not only hidden in the UI. Developer writes must fail in production and UAT. Analyst writes must fail in every bucket. User roles must be mapped consistently to FreeIPA groups and the relevant component authorization systems.

## Identity source and integration requirements

- FreeIPA is the central directory and Kerberos authority for human identities, groups, and service principals, using the existing `LAKEHOUSE.LOCAL` realm.
- Replace the standalone MIT KDC with FreeIPA through an isolated validation and staged cutover. Do not operate the two independent KDC databases as co-authorities for the same principals.
- Preserve service-principal names where compatible, but reissue the Kerberos keytabs under FreeIPA and securely update dependent services during cutover. The `write-service-account` RustFS S3 access key remains unchanged; its Kerberos keytab is explicitly in scope for replacement.
- FreeIPA groups are the canonical role assignments. Ranger UserSync consumes directory users and groups.
- Configure LDAP authentication or directory-backed authentication for supported interactive components, with component-specific role mapping. Account creation and group membership originate in FreeIPA.
- JupyterHub must authenticate `developer-user`, `analyst-user`, and the authorized platform administrator against FreeIPA over TLS. Access must be restricted to the intended FreeIPA groups; the non-interactive `write-service-account` must not be allowed to log into JupyterHub.
- JupyterHub LDAP authentication does not issue Kerberos tickets to notebook servers. Define and verify a separate secure per-user Kerberos ticket flow for Spark that does not persist user passwords or expose another user's credentials.
- RustFS retains its native IAM enforcement. The identity provisioner must reconcile directory identities/groups to RustFS users/groups and attach narrowly scoped policies; do not treat Ranger as an S3 policy engine.
- Preserve distinct service identities. `write-service-account` remains non-interactive; retain its existing RustFS S3 access key while reissuing its Kerberos keytab under FreeIPA.
- `user_a` and `user_b` must no longer receive interactive or data access after successful cutover. Keep their current credentials and persisted workspaces until the replacement identities pass verification; revoke old account access as part of cutover without deleting user data.

## Authorization requirements

- RustFS policies express the exact per-bucket read/write scopes in the matrix.
- Hive Metastore and direct Spark access must respect the same database-to-bucket/environment mapping. New database locations must be explicit and must not fall back into a broader bucket by default.
- StarRocks authorization uses Ranger policies for supported catalogs and objects. Ranger must not be presented as controlling direct Spark-to-RustFS requests.
- The configured StarRocks service identity may read the buckets needed for query execution, while Ranger authorizes each end-user query according to the matrix.
- Airflow and Jenkins operational roles remain separate from data roles; a data reader must not automatically receive Airflow or Jenkins administration.

## Migration and safety constraints

- Preserve the production `lake` bucket and its objects, the `write-service-account` RustFS S3 access key, and the platform `admin` identity and privilege mapping. Kerberos keytabs for service principals, including the writer, are reissued under FreeIPA as an approved migration step.
- Add new buckets and policies idempotently. Existing conflicting policies or database locations must cause a clear stop before mutation; never silently broaden access.
- Do not expose passwords, keytabs, access keys, or directory bind credentials in logs, Compose environment literals, SQL output, or generated documentation.
- The deployment remains a local proof of concept. Document FreeIPA container and Ranger operational limitations; do not claim production readiness.

## Verification acceptance criteria

- Create/resolve the two human accounts and role groups from FreeIPA; verify Kerberos tickets for the users and writer service principal.
- Verify bucket existence and exact RustFS permissions: developer read all/write dev only; analyst read prod only/write none; writer read/write all; admin retains administration.
- Verify representative Hive/Spark reads and writes on each environment path, including denied cross-environment writes.
- For direct Jupyter/Spark sessions, cross-environment database/table metadata may be visible; verify unauthorized data reads fail at RustFS using the user's own credentials, with no writer-identity fallback. Hive metadata DDL restrictions are not guaranteed by this requirement.
- Verify Ranger/StarRocks allows and denies queries according to the same role matrix, including newly created databases/tables where grants are intended to apply.
- Verify JupyterHub accepts valid members of the approved FreeIPA groups, rejects invalid credentials and non-members, and does not grant platform administrator privileges to data users. Separately verify the notebook's Kerberos ticket flow for Spark.
- Verify old `user_a` and `user_b` cannot authenticate or access data after cutover; verify persistent data and the writer's RustFS S3 access key are preserved and the replacement Kerberos keytabs work.
- Verify Airflow, Jenkins, and JupyterHub role mappings do not grant data or platform privileges beyond their assigned roles.

## Implementation assumptions to confirm in design

- FreeIPA uses the current `LAKEHOUSE.LOCAL` realm and becomes the sole authoritative KDC after staged cutover from the existing MIT KDC container.
- Role groups are named `lakehouse-developers`, `lakehouse-analysts`, and `lakehouse-writers`; platform `admin` remains separately privileged.
- Database locations follow bucket-scoped environment roots: `s3a://lake/warehouse/`, `s3a://lake-dev/warehouse/`, and `s3a://lake-uat/warehouse/`.
- Ranger is introduced for StarRocks authorization. The current project has Hive Metastore but no HiveServer2, so a HiveServer2 Ranger plugin is not assumed to protect direct Spark access.
