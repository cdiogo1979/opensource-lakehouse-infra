# User Stories — `default` Data Product Bootstrap

## Organization

Stories use the approved user-journey-based hybrid: platform-admin creation first, then independent role outcomes, then bootstrap verification and safe rerun behavior. Acceptance criteria use numbered business-rule checklists. Each criterion is observable and testable.

## US-01 — Initiate creation of the default data product

**As a** platform administrator, **I want** to run a documented CLI to create the `default` data product, **so that** the initial environment setup is consistent and repeatable.

**Requirements:** FR-01, FR-12, NFR-04, NFR-07

**Acceptance criteria**

1. The CLI accepts the approved `default` product operation and runs using the dedicated platform-admin identity.
2. The operation creates or validates resources for production, dev, and UAT in one journey.
3. The CLI reports completion or a safe actionable error without exposing secret values.
4. The CLI fails closed if required identity or service authentication is unavailable or invalid.

**INVEST note:** Independent entry point, valuable to operators, estimable as one workflow, small enough to review, and validated by observable command outcomes.

## US-02 — Provision environment-specific data-product resources

**As a** platform administrator, **I want** `default` provisioned in production, dev, and UAT, **so that** each environment has its own catalog namespace and object-storage location.

**Requirements:** FR-02, FR-03, FR-04, FR-05

**Acceptance criteria**

1. Production is represented by Polaris catalog `lakehouse`, namespace `default_lh`, and RustFS bucket `bucket-default`.
2. Dev is represented by Polaris catalog `lakehouse-dev`, namespace `default_lhdev`, and RustFS bucket `bucket-default-dev`.
3. UAT is represented by Polaris catalog `lakehouse-uat`, namespace `default_lhuat`, and RustFS bucket `bucket-default-uat`.
4. Each catalog uses the corresponding namespace-scoped path: `s3://bucket-default/default_lh/`, `s3://bucket-default-dev/default_lhdev/`, or `s3://bucket-default-uat/default_lhuat/`.
5. A resource from one environment is not configured to write under another environment’s bucket or prefix.

**INVEST note:** Each environment mapping is testable and separately verifiable; the shared product operation remains one coherent outcome.

## US-03 — Provision role groups and assign the creator as owner

**As a** platform administrator, **I want** the four product role groups created and the product creator assigned as owner, **so that** access can be granted through named roles without giving the creator realm-wide or object-store-root privileges.

**Requirements:** FR-06, FR-08, NFR-03, NFR-04

**Acceptance criteria**

1. Keycloak contains groups `role-default-developer`, `role-default-analyst`, `role-default-owner`, and `role-default-writer` after bootstrap.
2. Individual human users can be provisioned and assigned to these groups separately from product resource creation.
3. The creating platform-admin identity is assigned to `role-default-owner` for the new product.
4. Product-owner access does not grant Keycloak realm-admin or RustFS root privileges.
5. The dedicated writer service identity is assigned to `role-default-writer` and is not represented as a human login.

**INVEST note:** Group creation and initial owner assignment are a distinct, valuable onboarding outcome with independently observable identity state.

## US-04 — Read all environments and write only to dev

**As a** developer, **I want** to read product data in production, dev, and UAT but write only in dev, **so that** I can develop without changing protected environment data.

**Requirements:** FR-09, FR-10, FR-15, NFR-05

**Acceptance criteria**

1. A developer can read catalog metadata and table data in all three environments.
2. A developer can create or write product data in `lakehouse-dev.default_lhdev` and `bucket-default-dev`.
3. A developer write to production or UAT is denied by the relevant catalog or object-store authorization layer.
4. Direct object-store access cannot bypass the developer’s environment write boundary.

**INVEST note:** The developer’s distinct permission outcome is independent from bootstrap internals and has clear positive and negative probes.

## US-05 — Read production without write access

**As an** analyst, **I want** to read production product data without write access, **so that** I can analyze trusted data without changing it.

**Requirements:** FR-09, FR-10, FR-15, NFR-05

**Acceptance criteria**

1. An analyst can read production catalog metadata and table data in `lakehouse.default_lh` and `bucket-default`.
2. Analyst reads against dev or UAT are denied.
3. Analyst writes to production, dev, and UAT are denied.
4. Direct S3 requests cannot bypass the analyst’s read-only, production-only boundary.

**INVEST note:** This is an independent read-only policy outcome with observable allowed and denied operations.

## US-06 — Manage the product as owner

**As a** data-product owner, **I want** to manage product objects and product-level grants across all three environments, **so that** I can administer `default` without holding platform-wide identity or storage-root privileges.

**Requirements:** FR-08, FR-10, FR-15, NFR-05

**Acceptance criteria**

1. An owner can manage product objects and product-level catalog grants in production, dev, and UAT.
2. The owner’s authority is limited to the `default` product resources and approved buckets/catalogs.
3. The owner cannot administer the Keycloak realm or use RustFS root credentials solely by virtue of product ownership.
4. Owner grant changes take effect in Polaris and RustFS authorization behavior.

**INVEST note:** Product ownership is distinct from platform administration and can be independently tested through allowed and denied administrative actions.

## US-07 — Write through the automated service identity

**As an** automated writer service, **I want** to authenticate non-interactively and read/write all three environments, **so that** bootstrap and approved Spark workloads can create and verify product data.

**Requirements:** FR-07, FR-09, FR-10, FR-12, FR-14, FR-15, NFR-04, NFR-05

**Acceptance criteria**

1. The writer service identity obtains OAuth credentials without Kerberos or interactive human login.
2. The identity can read and write catalog and object data in production, dev, and UAT.
3. The identity has no Keycloak realm-admin or RustFS root privileges.
4. Invalid, unavailable, or insufficient credentials fail closed.
5. OAuth client secrets or fallback scoped credentials are never printed or stored in source-controlled configuration.

**INVEST note:** The service actor has a clear system goal and authorization boundary; the outcome is independently testable without modeling it as a human persona.

## US-08 — Verify initial tables and safely repeat bootstrap

**As a** platform administrator, **I want** the bootstrap to create a smoke-test table in every environment and safely validate a rerun, **so that** I can confirm catalog, storage, authorization, and setup integrity.

**Requirements:** FR-11, FR-15, NFR-01, NFR-07

**Acceptance criteria**

1. Each namespace contains `bootstrap_smoke_test` with the approved deterministic schema and one sample row.
2. Spark can read the sample row and the Iceberg files are stored under the matching environment bucket prefix.
3. A second bootstrap run validates matching resources and tables without deleting data or creating duplicate resources.
4. A conflicting pre-existing named resource causes an actionable failure rather than automatic deletion or replacement.
5. Verification reports success only when all three environment resource sets and smoke tables pass.

**INVEST note:** Verification and rerun safety form an independently valuable operator outcome with deterministic acceptance evidence.

## Persona-to-story mapping

| Persona | Stories |
|---|---|
| Platform Administrator | US-01, US-02, US-03, US-08 |
| Data Product Owner | US-06 |
| Developer | US-04 |
| Analyst | US-05 |
| Automated Writer | US-03, US-07 |

## Requirement traceability

| Requirement | Story coverage |
|---|---|
| FR-01 | US-01 |
| FR-02–FR-05 | US-02 |
| FR-06, FR-08 | US-03, US-06 |
| FR-07, FR-12, FR-14 | US-07 |
| FR-09, FR-10 | US-04–US-07 |
| FR-11 | US-08 |
| FR-15 | US-04–US-08 |
| NFR-01 | US-08 |
| NFR-03, NFR-04 | US-01, US-03, US-07 |
| NFR-05 | US-04–US-07 |
| NFR-07 | US-01, US-08 |
