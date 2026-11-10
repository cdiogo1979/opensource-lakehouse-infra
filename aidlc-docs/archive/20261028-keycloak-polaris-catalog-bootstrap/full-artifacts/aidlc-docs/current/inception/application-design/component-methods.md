# Application Component Methods

These are interface-level contracts. Detailed validation rules, retries, error taxonomy, and policy statements belong to the per-unit Functional and NFR Design stages. `ProductSpec`, `BootstrapOptions`, `CredentialBundle`, and result types are logical DTOs to be defined during code generation. Secrets are opaque handles/streams and must never be rendered in reports.

## Platform Admin CLI

```text
bootstrap_default(options: BootstrapOptions) -> BootstrapReport
verify_default(options: VerificationOptions) -> VerificationReport
```

Accepts the approved product (`default`), environment set, service endpoints, and a protected credential source. Emits a redacted report and nonzero status on incomplete setup.

## Bootstrap Coordinator

```text
run_bootstrap(
    product: ProductSpec,
    options: BootstrapOptions,
    adapters: ProviderAdapters,
    spark_runner: SparkJobRunner,
) -> BootstrapReport
```

Invokes ordered idempotent provider operations, preserves successfully created resources after a later failure, and allows a rerun to validate/reconcile. It does not delete resources.

## Keycloak Adapter

```text
ensure_product_groups(product: ProductSpec) -> GroupSet
ensure_writer_identity(product: ProductSpec) -> ServiceIdentityRef
assign_owner(user_ref: UserRef, product: ProductSpec) -> MembershipResult
read_group_memberships(user_ref: UserRef) -> GroupMemberships
```

Ensures product groups and writer identity; human account lifecycle remains in Keycloak and outside the product bootstrap. Does not grant realm administration to product roles.

## Polaris Adapter

```text
ensure_catalogs(product: ProductSpec) -> CatalogSet
ensure_namespaces(product: ProductSpec) -> NamespaceSet
ensure_principals_and_roles(product: ProductSpec) -> PolarisRoleBindings
verify_grants(product: ProductSpec) -> GrantVerification
```

Configures OIDC principal and principal-role claim mapping, creates the Polaris principals/roles/grants needed by the approved access matrix, and checks expected catalog authorization. The exact handling of newly provisioned human principals must align with the pinned Polaris external-auth mode.

## RustFS Adapter

```text
ensure_buckets(product: ProductSpec, credentials: CredentialHandle) -> BucketSet
validate_storage_configuration(product: ProductSpec) -> StorageConfigurationResult
```

Creates or validates buckets and the Polaris-facing S3-compatible configuration using the protected bootstrap identity. Does not provision direct end-user credentials.

## Spark Job Runner and Smoke Job

```text
run_smoke_job(job_spec: SmokeJobSpec, writer_credentials: CredentialHandle) -> JobResult
create_or_validate_smoke_table(catalog: CatalogRef, namespace: NamespaceRef) -> TableVerification
```

Runs the approved one-shot workload with writer OAuth credentials, creates/validates the deterministic smoke table, and returns status without token or storage-key values.

## Readiness and Report Builder

```text
wait_ready(dependencies: Sequence[ServiceDependency], timeout: Duration) -> ReadinessReport
build_report(steps: Sequence[StepResult]) -> BootstrapReport
```

Reports provider readiness and per-step outcomes while redacting secrets and sensitive token fields.
