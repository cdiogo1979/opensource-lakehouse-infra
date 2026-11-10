# Application Components — `default` Data Product Bootstrap

## Scope

This is the high-level component model for the approved initial journey. It covers Keycloak, Polaris, RustFS, the platform-admin CLI, and a one-shot Spark smoke job. Airflow, JupyterHub, Jenkins, and StarRocks are deferred. The design assumes user and writer data access occurs through Polaris-aware Iceberg clients with Polaris-vended, short-lived RustFS credentials; ordinary users do not receive direct S3 credentials.

## Components

| Component | Responsibility | High-level interface |
|---|---|---|
| Platform Admin CLI | Provides the documented `default` product bootstrap and verification entry points; validates inputs and presents safe progress/errors. | `bootstrap_default(options) -> BootstrapReport`; `verify_default(options) -> VerificationReport` |
| Bootstrap Coordinator | Runs ordered, idempotent provider operations, records step outcomes, and invokes the smoke job only after prerequisites are ready. | `run_bootstrap(request, providers, spark_runner) -> BootstrapReport` |
| Keycloak Adapter | Ensures the target realm/client integration, four product groups, writer service identity, and initial owner membership exist. Human users remain provisioned separately. | `ensure_product_groups(product)`; `ensure_writer_identity(product)`; `assign_owner(user, product)`; `read_group_memberships(user)` |
| Polaris Adapter | Ensures catalogs, namespaces, principal roles, catalog roles, grants, and external OIDC principal/role mapping. Provides the authorization path used by Iceberg clients. | `ensure_catalogs(product)`; `ensure_namespaces(product)`; `ensure_principals_and_roles(product)`; `verify_grants(product)` |
| RustFS Adapter | Ensures the three buckets and the catalog storage configuration needed for controlled access. Uses a protected bootstrap credential; it does not distribute long-lived end-user S3 keys. | `ensure_buckets(product)`; `validate_storage_configuration(product)` |
| Spark Job Runner | Starts the short-lived Spark process with the writer OAuth identity and approved Polaris catalog configuration. | `run_smoke_job(job_spec) -> JobResult` |
| Smoke Job | Creates or validates `bootstrap_smoke_test` in each namespace and checks the expected sample row and environment path through Iceberg REST. | CLI job arguments/config; structured result |
| Bootstrap Credential Source | Supplies protected platform bootstrap credentials to the CLI/adapters without printing or persisting secret values in source/config. | `load_provider_credentials() -> CredentialBundle` |
| Readiness and Report Builder | Waits for provider readiness, aggregates created/validated/failed steps, and redacts sensitive fields from errors. | `wait_ready(dependencies)`; `build_report(step_results)` |

## Identity and authorization boundary

- Keycloak groups carry the product role memberships. OIDC tokens expose the group/role claim in the agreed Polaris claim path and role naming format.
- Polaris resolves each caller to a Polaris principal and principal role, then applies explicit catalog role grants to catalogs/namespaces/tables. The bootstrap must create the required Polaris RBAC entities; a Keycloak group claim alone does not create Polaris grants.
- Spark and other Iceberg clients request vended credentials through the Polaris REST protocol. Polaris issues short-lived storage credentials consistent with the authorized table location/operation.
- End users and the writer do not get direct RustFS credentials. The platform admin uses a distinct protected bootstrap credential for provider setup, including bucket creation. Keep its permissions limited to setup operations.
- Direct S3 API attempts by ordinary roles are denied because no credentials are issued to those roles outside the Polaris-vended Iceberg path.

## Product and environment model

| Environment | Polaris catalog | Namespace | RustFS bucket/base path |
|---|---|---|---|
| Production | `lakehouse` | `default_lh` | `bucket-default/default_lh/` |
| Development | `lakehouse-dev` | `default_lhdev` | `bucket-default-dev/default_lhdev/` |
| UAT | `lakehouse-uat` | `default_lhuat` | `bucket-default-uat/default_lhuat/` |

The resource model follows the approved requirements. Exact APIs, storage integration settings, and authentication claim paths are version-specific and remain subject to Infrastructure Design and integration tests.
