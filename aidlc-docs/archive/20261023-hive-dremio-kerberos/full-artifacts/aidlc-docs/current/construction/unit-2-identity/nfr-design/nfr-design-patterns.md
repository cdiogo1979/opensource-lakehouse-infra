# Unit 2 Identity Provisioning — NFR Design Patterns

## Scope

These patterns translate the approved Unit 2 NFRs into logical implementation guidance for the local identity/permission provisioning workflow. They do not select concrete APIs, Compose syntax, image tags, file names, healthcheck commands, or policy documents. Those details belong to Infrastructure Design and Code Generation. The patterns do not certify native account support or authorization behavior for any component.

## Readiness and Dependency Gating

- Treat the identity provisioner as an explicit one-shot operation, separate from the health state of long-running services.
- Before any mutation, validate that the KDC and Hive Metastore are healthy, PostgreSQL and RustFS are ready, bucket initialization succeeded, Dremio initial setup is complete, and required protected setup credentials are readable.
- Do not infer component readiness from a running container. Use each component's readiness contract and fail before mutation when a required dependency is unavailable.
- Model initial identity setup and post-ETL reader grants as distinct phases. The initial phase provisions principals/accounts and initial writer capability. The reader-grant phase waits until Unit 3 has created `databaseA` and `databaseB`.
- Downstream ETL and user authorization scenarios remain blocked until required identity setup reports success. Deferred work must be reported as deferred, never as complete.

## Component Adapter Pattern

- Keep KDC, RustFS, Dremio, PostgreSQL, and Hive/Hadoop setup behind small component-owned adapters invoked by one operator action.
- Each adapter receives only its own setup credential references and writes only identities/grants owned by that component.
- Do not add a central policy engine or persistent identity store. The provisioner coordinates setup and records results; components retain their own authorization decisions.
- Spark consumes caller Kerberos and RustFS credentials; no separate Spark account directory is introduced. JupyterHub user/session mapping remains Unit 5 work.
- If a component lacks a supported interface or cannot grant the requested permission, the adapter returns a clear unsupported/failed result and the required flow stops. Do not substitute admin access or silently weaken policy.

## Credential Isolation and Delivery

- Store component admin/setup credentials and generated user credentials in the ignored, host-restricted runtime credential directory.
- Pass file references to component adapters rather than placing secret values in command-line arguments, general environment variables, logs, or reports.
- Restrict each adapter to the credential files it needs. Mount input files read-only where supported; write newly generated files with restrictive host permissions.
- Maintain distinct Kerberos keytabs, Dremio passwords, RustFS access keys/secrets, and PostgreSQL role passwords. Native admin credentials are separate across components; the writer and test-user credentials are separate from admin.
- Never expose the Hive Metastore PostgreSQL service credential to Spark ETL or user sessions.
- Rotation is a separate explicit operation: identify dependent services, rotate in the owning component, update protected local artifacts, then restart/update consumers in a documented order. Ordinary provisioning never rotates values.

## Idempotency, Retry, and Failure Recovery

- Use ensure-style operations that distinguish `created` from `already-present` and preserve existing credentials and permissions on normal reruns.
- Retry only bounded dependency-availability waits or explicitly known-safe idempotent operations. Do not retry authentication, authorization, incompatible-state, or unsupported-capability errors as transient failures.
- Stop at the first failed required operation. Return an incomplete/failed result with component and action context, and redact secrets from diagnostics.
- Preserve all successful earlier component changes for diagnosis and safe rerun. Do not automatically delete accounts, principals, keytabs, policies, database metadata, or data.
- A failed run never reports overall setup complete. The operator reviews the partial result, addresses the cause, and reruns the ensure workflow.

## Execution Order and Scale

- Provision the fixed PoC identity set sequentially in dependency order. Do not add concurrency, bulk provisioning, replicas, or scale-out support.
- Keep component-native account setup separate from Kerberos principal creation so one system's success does not imply another system's success.
- Do not add retries or optimization based on a performance target; none was approved.

## Operator Reporting

- Report one status per identity and component using `created`, `already-present`, `deferred`, or `failed`.
- Include the operation and a safe diagnostic for failures; omit credential values, keytab contents, ticket data, and RustFS secret keys.
- Distinguish configured permissions from verified authorization. Account creation or grant setup is not evidence that Spark or Dremio enforces the expected effective-user outcome.
- Direct the operator to the post-ETL reader-grant phase after Unit 3 data setup; do not report reader grants as configured before databases exist.
- Use command output and container logs for this local single-operator workflow. Do not add a report database, monitoring stack, alerting system, or UI.

## Local Operation and Feasibility Boundary

- Keep provisioner connections on the Compose network and host-published interfaces loopback-only.
- Keep the provisioner one-shot; there is no availability or performance SLA and no persistent identity-management service.
- RustFS prefix-policy support, Hive writer/read grants over RustFS, Dremio non-admin Space write, and native admin mappings are verification gates. If a gate fails, record the behavior and request review of the smallest change before altering versions, boundaries, or privileges.

## NFR Traceability

| Design concern | Approved requirements |
|---|---|
| Fixed local identity set and no scale target | U2-NFR-01 to U2-NFR-05 |
| Persistent credentials and explicit rotation | U2-NFR-07 to U2-NFR-09 |
| Credential isolation, local storage, and least privilege | U2-NFR-10 to U2-NFR-16 |
| Version compatibility and capability gates | U2-NFR-17 to U2-NFR-20 |
| Readiness, retries, fail-fast results, and redacted logs | U2-NFR-21 to U2-NFR-26 |
| Maintainable adapters and operator workflow | U2-NFR-27 to U2-NFR-30 |

## Extension Applicability

- Security Baseline extension: disabled; approved secret isolation and least-privilege requirements remain mandatory.
- Property-Based Testing extension: partial; not applicable to this design-only artifact stage unless implementation adds pure testable transforms.
- Resiliency Baseline extension: disabled; safe reruns and failure preservation are still required by approved NFRs.
