# Requirements — Keycloak, Polaris, and `default` Data Product Bootstrap

## Intent analysis

- **User request:** Start a new intent to replace FreeIPA with Keycloak and Hive Metastore with Apache Polaris; remove the old FreeIPA/Hive setup; bootstrap three environment catalogs, databases/namespaces, buckets, and four role groups. The initial user journey is a platform admin creating the first data product named `default`, including one test table in each database.
- **Request type:** Infrastructure capability and cross-component replacement.
- **Scope estimate:** System-wide infrastructure change across identity, catalog, object storage, bootstrap tooling, and Spark smoke-test integration.
- **Complexity estimate:** Complex. OAuth/OIDC authentication, Polaris authorization, RustFS storage policies, and Iceberg REST integration must work together.
- **Delivery approach:** Staged journey. This increment delivers the platform-admin data-product bootstrap only. Airflow, JupyterHub, Jenkins, and StarRocks integrations are deferred.
- **Data approach:** No migration. Resources are freshly created. Bootstrap is non-destructive and safe to rerun.

## User journey

1. A platform operator provisions or uses a dedicated initial platform-admin identity using a protected one-time bootstrap secret.
2. The operator runs the documented idempotent CLI/script to create the `default` data product.
3. Bootstrap creates the Keycloak groups, Polaris catalogs/namespaces and role grants, RustFS buckets and scoped policies, and the dedicated writer service identity.
4. The creating platform admin is assigned the product-owner role.
5. A short-lived Spark job authenticates using OAuth, creates `bootstrap_smoke_test` with a deterministic schema and one sample row in each environment namespace, and writes objects to that environment’s bucket path.
6. Verification checks that resources exist, expected role permissions succeed, denied actions fail, and a second bootstrap run does not destroy or duplicate resources.

## Functional requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| FR-01 | Provide a documented, idempotent platform-admin CLI/script to create the initial data product named `default`. | Clean local Compose bootstrap completes and reports created/validated resources without printing secrets. |
| FR-02 | Create three Polaris Iceberg REST catalogs: `lakehouse`, `lakehouse-dev`, and `lakehouse-uat`. | Polaris Management API lists all three catalogs. |
| FR-03 | Create one namespace per catalog, using the requested database names: `default_lh` in `lakehouse`, `default_lhdev` in `lakehouse-dev`, and `default_lhuat` in `lakehouse-uat`. | Each namespace is visible through the Polaris catalog API and usable by Spark. |
| FR-04 | Create three RustFS buckets: `bucket-default`, `bucket-default-dev`, and `bucket-default-uat`. | RustFS confirms bucket existence and permitted access. |
| FR-05 | Configure each catalog’s Iceberg base location to a namespace-scoped path: `s3://bucket-default/default_lh/`, `s3://bucket-default-dev/default_lhdev/`, and `s3://bucket-default-uat/default_lhuat/`. | Spark writes table objects beneath the matching bucket/prefix; no cross-environment location is used. |
| FR-06 | Create the Keycloak groups `role-default-developer`, `role-default-analyst`, `role-default-owner`, and `role-default-writer`. Provision users separately and assign memberships in Keycloak. | Keycloak Admin API lists groups; memberships can be managed independently of resource creation. |
| FR-07 | Create a dedicated writer service identity and assign it to `role-default-writer`; it can obtain non-interactive OAuth credentials for the bootstrap Spark job. | Spark obtains a token without Kerberos and completes a write/read test. Secret material is not logged. |
| FR-08 | Map Keycloak identities/groups to Polaris principals and Polaris RBAC grants. The creating platform admin is assigned to `role-default-owner`. | Test tokens resolve to the intended Polaris principal/roles; owner can administer product grants without realm-admin privileges. |
| FR-09 | Apply role permissions consistently to Polaris metadata operations and RustFS object access. | Positive and negative tests in FR-15 demonstrate both catalog authorization and direct S3 authorization boundaries. |
| FR-10 | Implement the agreed access matrix: developer reads production, dev, and UAT and writes only dev; analyst reads production only and cannot write; writer reads/writes all three; owner manages product objects and grants in all three. | Authentication tests for each role verify allowed and denied operations across the three environments. |
| FR-11 | Create `bootstrap_smoke_test` in each namespace with a deterministic schema and one sample row, stored under that environment’s bucket prefix. | Spark can create the table, insert/read the sample row, and confirm the Iceberg metadata/data files are in the intended bucket. |
| FR-12 | Use Keycloak OIDC for human authentication and OAuth/STS for service-to-service and S3 access where supported; use scoped credentials as a documented fallback. | End-to-end Spark test uses no Kerberos. Any fallback credentials are least-privilege, file/secret-backed, and verified not to appear in logs. |
| FR-13 | Remove FreeIPA and Hive Metastore setup, including Hive schema initialization and Hive-only metadata configuration, from the new default deployment. | Default Compose configuration has no FreeIPA or Hive service/dependency. Repository references are classified as removed, retained historical documentation, or deferred before deletion. |
| FR-14 | Remove MIT Kerberos/KDC and Kerberos configuration/keytab dependencies in this intent. Integrations for deferred services are not represented as migrated or verified. | Initial Compose journey starts without a KDC; the included Spark bootstrap completes using OAuth. No default journey script requires keytabs or `kinit`. |
| FR-15 | Provide a clean bootstrap test with positive and negative access checks for all four roles across Polaris and RustFS, covering resource creation and safe reruns. | Automated test evidence verifies all catalogs, namespaces, buckets, smoke tables, allowed operations, denied operations, and idempotent rerun behavior. |

## Role and permission matrix

| Role/group | Polaris catalog/data access | RustFS object access | Administrative boundary |
|---|---|---|---|
| `role-default-developer` | Read all environments; write dev only | Read all buckets; write only `bucket-default-dev` | No Keycloak realm administration or bucket-policy administration |
| `role-default-analyst` | Read production only; no writes | Read only `bucket-default`; no writes | No administrative rights |
| `role-default-owner` | Manage product objects and grants across all three catalogs | Manage product data/policies across the three product buckets, excluding RustFS root credentials | Product-level ownership only; no Keycloak realm-admin rights |
| `role-default-writer` | Read/write in all three catalogs | Read/write in all three buckets | Non-interactive service identity; no realm-admin or RustFS root rights |

The platform-admin bootstrap identity is a separately provisioned operator identity, not a replacement for the Keycloak realm administrator or RustFS root account. The product creator receives the owner group membership as approved.

## Non-functional requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| NFR-01 | Bootstrap is idempotent and non-destructive by default: create missing resources, validate matching resources, and fail on conflicts. It never deletes bucket data automatically. | Run twice; compare resources/data; confirm no deletion or duplicate creation. Conflicting resources produce an actionable failure. |
| NFR-02 | Local deployment uses Docker Compose on one developer machine. Administrative UIs bind to loopback by default. | Compose configuration and host port inspection show loopback-only bindings for admin interfaces. |
| NFR-03 | Persistent metadata is isolated: Polaris receives a dedicated PostgreSQL database/service; Keycloak receives a supported persistent production-mode database configuration. | Restart services and verify identity, group, catalog, namespace, and grant state persists. Polaris does not use the retired Hive schema. |
| NFR-04 | Secrets are generated/provided through protected files or Compose secrets and are never printed in command output, checked into source, or embedded in table/catalog configuration. | Static secret-safety checks and log review pass. |
| NFR-05 | Authorization fails closed when identity provider, token validation, Polaris grants, or RustFS policies are unavailable or invalid. | Negative tests reject missing, invalid, expired, or underprivileged credentials. |
| NFR-06 | Images and client libraries are pinned to supported versions/digests during design and verified together in Build and Test. | Version matrix is documented; clean image builds and integration tests pass. |
| NFR-07 | The bootstrap provides actionable readiness and error reporting without exposing credentials. | Failure-injection checks produce nonzero exit status and safe diagnostic messages. |
| NFR-08 | Property-based testing is required partially: apply it to pure functions and serialization round-trips. | Applicable unit/property tests execute in the configured test pipeline. |

No availability, throughput, latency, RTO, or RPO target has been specified. Resiliency baseline extension is disabled by user choice; this does not waive functional reliability or safe bootstrap requirements above.

## Initial Compose scope

The initial journey starts Keycloak, Polaris, its PostgreSQL persistence, RustFS, bootstrap helpers, and a short-lived Spark job for smoke-table creation. Airflow, JupyterHub, Jenkins, and StarRocks are deferred from the default startup for this journey. The deferred services are not claimed to work with Keycloak/Polaris after this intent unless separately integrated and tested.

## Assumptions and constraints

- Polaris catalogs are top-level catalogs; the requested “databases” are one top-level namespace within each catalog.
- `default` is the initial data product and creates resources for production, dev, and UAT together.
- Existing data does not need migration. Existing named resources are validated; conflicting state causes failure rather than deletion.
- The platform admin creates the four Keycloak groups; individual users are provisioned separately. The creating operator is assigned to the owner group.
- Keycloak is the human identity provider and supplies OAuth tokens; Polaris still enforces its own internal RBAC grants. The RustFS identity claim/policy and STS behavior must be integration-tested for the pinned RustFS version.
- MIT Kerberos is removed from the target stack; the bootstrap Spark job uses OAuth. Airflow, JupyterHub, and StarRocks are deferred.
- Polaris metadata is stored in a dedicated PostgreSQL database/service, separate from the former Hive schema and Airflow metadata.
- Security Baseline extension: disabled. Property-Based Testing extension: partial, for pure functions and serialization round-trips. Resiliency Baseline extension: disabled.

## Verified product integration references

- Apache Polaris documents Keycloak external authentication with its built-in authorizer. In that mode the authenticated principal must exist in Polaris and receive Polaris metastore grants; this is the basis for FR-08 and remains an integration test requirement: [Polaris Keycloak guide](https://polaris.apache.org/guides/keycloak/).
- Apache Polaris documents an integration using RustFS as S3-compatible storage and Spark through the Iceberg REST catalog with vended credentials: [Polaris RustFS guide](https://polaris.apache.org/guides/rustfs/).
- RustFS documents OIDC Console SSO, policy mapping from token claims, and STS credentials; exact machine-client flow and permission mapping must be verified against the pinned version: [RustFS OIDC](https://docs.rustfs.com/en/security-compliance/oidc), [RustFS IAM](https://docs.rustfs.com/en/security-compliance/iam).
- Polaris’s RBAC model separates principal roles, catalog roles, and object privileges: [Polaris 1.8.0 access control](https://polaris.apache.org/releases/1.8.0/managing-security/access-control/).

## Extension configuration

| Extension | Enabled | Decision |
|---|---|---|
| Security Baseline | No | User selected no |
| Property-Based Testing | Partial | User selected pure functions and serialization round-trips |
| Resiliency Baseline | No | User selected no |
