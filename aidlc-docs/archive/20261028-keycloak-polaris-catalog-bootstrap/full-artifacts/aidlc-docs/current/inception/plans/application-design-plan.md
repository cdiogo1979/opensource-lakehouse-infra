# Application Design Plan — Keycloak + Polaris `default` Bootstrap

## Scope and baseline

Design the approved platform-admin journey and its role outcomes from US-01–US-08. The target replaces FreeIPA with Keycloak and Hive Metastore with Polaris, and uses RustFS plus Spark for storage and smoke-table creation. Airflow, JupyterHub, Jenkins, and StarRocks remain deferred. Requirements and stories are the approved product baseline; the existing canonical architecture documents describe the prior system and must be treated as legacy context, not as current target decisions.

Application Design will establish high-level component responsibilities, contracts, service orchestration, and dependencies. Detailed reconciliation rules, failure semantics, policy statements, and test procedures remain for Functional/NFR Design.

## Planning checklist

### Analyze context

- [x] Read approved requirements, stories/personas, execution plan, and current canonical architecture context.
- [x] Identify the journey components: operator interface, bootstrap coordinator, Keycloak identity, Polaris catalog/RBAC, RustFS buckets/IAM, and Spark Iceberg smoke job.
- [x] Keep deferred clients outside the application design scope.
- [x] Collect answers to the six design questions.
- [x] Review answers against approved requirements and verify the Polaris authentication/authorization boundary.
- [x] Resolve the direct object-store access boundary in follow-up Question 7.

### Design approval gate

- [x] User completed all `[Answer]:` fields.
- [x] Review answers and resolve the ambiguity in Question 7.
- [x] Obtain explicit approval of this completed plan before generating design artifacts.

### Generate mandatory artifacts after plan approval

- [x] Generate `aidlc-docs/current/inception/application-design/components.md` with component names, responsibilities, and high-level interfaces.
- [x] Generate `component-methods.md` with method signatures, purpose, and input/output types; defer detailed business rules.
- [x] Generate `services.md` with service boundaries and orchestration.
- [x] Generate `component-dependency.md` with dependency relationships, communication patterns, and data flow.
- [x] Generate consolidated `application-design.md`.
- [x] Validate completeness and consistency against requirements and US-01–US-08.
- [ ] Present the artifacts for explicit design approval; record approval in the audit and state before proceeding.

## Design questions

Answer each question by replacing its `[Answer]:` line. Recommended options are suggestions for the architecture, not decisions until accepted.

### Question 1 — Bootstrap entry point and execution boundary

Where should the platform administrator invoke product creation?

A) A documented host CLI that calls service APIs and launches the one-shot Spark job through Compose (Recommended: simple operator workflow, explicit stages, no permanently running admin service).

B) A one-shot bootstrap container invoked with `docker compose run`, with a thin host wrapper only for convenience.

C) A long-running admin API/UI service.

X) Other (describe after `[Answer]:`).

[Answer]:A

### Question 2 — Keycloak group mapping into Polaris

How should Keycloak groups affect Polaris authorization? Polaris has its own principal and role/grant model, so an OIDC group claim alone may not create Polaris objects or grants.

A) Configure Keycloak group claims to map to Polaris principal roles, and bootstrap the matching Polaris principals, principal roles, catalog roles, and grants. Validate claim transformation and principal resolution against the pinned Polaris version (Recommended; Polaris RBAC still requires explicit Polaris entities and grants).

B) Use a bootstrap-managed mapping layer that resolves Keycloak groups and applies Polaris grants through the Management API; users authenticate to Polaris with OIDC, while provisioning stays explicit.

C) Use a bootstrap reconciler for Polaris principal/role/grant lifecycle, while Keycloak claims resolve each authenticated user to the pre-created Polaris principal role (combines identity mapping and explicit grants).

X) Other (describe after `[Answer]:`).

[Answer]:A

### Question 3 — RustFS authorization path

How should human and writer roles receive scoped S3 access consistent with the same group matrix?

A) Use RustFS OIDC/STS integration and map validated Keycloak claims/groups to RustFS policies; verify the service-to-service and temporary-credential flow against the pinned RustFS version (Recommended if supported end to end).

B) Have the bootstrap provision scoped RustFS IAM users/policies and deliver per-user/service credentials through a documented secret mechanism; group changes are reconciled into policy membership.

C) Use Polaris-vended temporary storage credentials for Spark/Iceberg access, while direct RustFS access for role testing and other clients uses scoped RustFS IAM policies.

X) Other (describe after `[Answer]:`).

[Answer]: X — use Polaris-vended temporary storage credentials for all users except the platform administrator.

### Question 4 — Product owner grant authority

US-06 allows an owner to manage product-level catalog grants and object access, while forbidding realm-admin and RustFS-root authority. Where should grant changes be made?

A) Owner uses Polaris product-scoped roles/grants; RustFS bucket policies remain platform-managed, and owner changes are limited to Polaris objects/grants (Recommended for least privilege).

B) Owner uses a narrowly scoped product administration API that validates requests and updates both Polaris grants and RustFS policies; owners never receive provider administrator credentials.

C) Owner can edit both Polaris and RustFS policies directly using product-scoped provider roles, if those providers support enforceable resource-level administration.

X) Other (describe after `[Answer]:`).

[Answer]:A

### Question 5 — Provisioning sequence and partial completion

How should the coordinator behave when one provider fails after earlier resources were created? Requirements forbid destructive cleanup and require safe reruns.

A) Run ordered, idempotent reconcile steps; stop at the first failure, report completed/failed steps, preserve created resources, and let the next run validate/reconcile them (Recommended).

B) Attempt compensating rollback of resources created during the run, but never delete pre-existing data.

C) Run independent provider steps concurrently and collect all errors before returning.

X) Other (describe after `[Answer]:`).

[Answer]:A

### Question 6 — Application component grouping

Which high-level organization should the component model use?

A) A thin orchestration layer with separate provider adapters for Keycloak, Polaris, and RustFS, plus a Spark job launcher/verifier (Recommended: explicit provider boundaries and independently testable contracts).

B) One bootstrap component that owns provider-specific logic and Spark execution.

C) Separate user-facing services for identity, catalogs, storage, and Spark, coordinated by the CLI.

X) Other (describe after `[Answer]:`).

[Answer]:A

## Answer analysis and follow-up

Answers 1, 2, 4, 5, and 6 select coherent design directions. For Question 2, the design must provision Polaris principals, principal roles, catalog roles, and grants, then map Keycloak group claims to the Polaris principal roles; a group claim by itself does not replace Polaris RBAC grants.

Question 3 selects Polaris-vended temporary storage credentials for users and writer, with platform admin as an exception. This is appropriate for Iceberg clients authorized through Polaris, but does not itself grant general-purpose direct S3 API access. The approved stories require storage access to respect the role matrix and must not allow direct object-store calls to bypass it. The intended platform-admin exception also needs a defined bootstrap credential boundary for creating buckets and configuring Polaris storage. Please answer Question 7 below so the design distinguishes Iceberg table access from direct object-store access.

### Question 7 — Direct RustFS access versus Polaris-vended credentials

Which access contract should apply to developers, analysts, owners, and the writer?

A) Human and writer identities access table data through Polaris-aware Iceberg clients only. Polaris authorizes catalog operations and vends short-lived, location-scoped RustFS credentials for those operations; direct S3 API access using user-held credentials is not provided. Platform admin uses a separate protected bootstrap credential only for bucket/policy provisioning (Recommended; preserves a single user-facing authorization path).

B) Polaris vends temporary credentials for Iceberg clients, and users also receive direct S3 credentials/policies for non-Iceberg object operations; both paths must independently implement the same role matrix.

C) Other (state which users need direct S3 API access and the authorization source for each).

[Answer]:A

## Answer review and gate

All answers are complete and consistent with the approved requirements and US-01–US-08. Question 7 confirms that human and writer identities access table data through Polaris-aware Iceberg clients, with Polaris vending short-lived, location-scoped RustFS credentials. Users receive no direct S3 credentials. The platform administrator uses a separate protected bootstrap credential for bucket/policy provisioning.

The completed plan was approved by the user on 2026-10-28. The five application design artifacts listed above have been generated. They await separate design approval. No application code or runtime services have been changed.
