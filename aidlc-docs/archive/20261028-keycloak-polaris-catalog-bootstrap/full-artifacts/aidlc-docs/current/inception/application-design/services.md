# Application Services and Orchestration

## Runtime service inventory for this journey

| Service/process | Lifetime | Purpose |
|---|---|---|
| Keycloak | Long-running Compose service | OIDC provider, realm/client configuration, product groups, writer client identity |
| Polaris | Long-running Compose service | Iceberg REST and Management APIs, catalog RBAC, credential vending |
| Polaris PostgreSQL | Long-running Compose service with persistent volume | Polaris metadata persistence, isolated from retired Hive metadata |
| RustFS | Long-running Compose service with persistent storage | S3-compatible object storage and bucket administration |
| Bootstrap CLI | Short-lived host process | Operator entry point and ordered orchestration of setup |
| Spark smoke job | Short-lived Compose job/container | Creates and verifies the three Iceberg smoke tables using writer OAuth |

There is no always-on bootstrap API or UI in this design. Compose service selection and detailed health checks are defined in Infrastructure Design.

## Bootstrap service flow

1. The platform administrator invokes the CLI with the `default` product operation.
2. The CLI loads protected bootstrap credentials and confirms service readiness without displaying secret values.
3. The coordinator ensures Keycloak groups, writer service identity, and the creator’s owner membership.
4. It ensures RustFS buckets and Polaris storage integration settings.
5. It ensures Polaris catalogs, namespaces, principals, principal roles, catalog roles, and grants.
6. It launches the smoke job only after the identity, catalog, and storage prerequisites are ready. The job authenticates non-interactively as the writer and uses Polaris Iceberg REST with credential vending.
7. The CLI verifies the expected resources and table sample rows, then prints a redacted per-environment report.

The ordering is intentional and idempotent. If a step fails, later steps do not run; already created state is retained and reported. A rerun validates matching state and continues. No automatic compensating deletion is performed.

## User and service authentication

- Human users authenticate through Keycloak OIDC. Group/role claims are mapped to Polaris principal roles.
- The writer uses a non-interactive Keycloak OAuth client credential and is mapped to the writer role. Its client secret is provided from protected runtime secret storage.
- The Spark client requests Polaris-vended short-lived RustFS credentials for Iceberg table operations. Human and writer users receive no direct S3 credentials.
- The platform administrator’s bootstrap identity is separate from ordinary product roles and from Keycloak realm-admin/RustFS root. Its protected credentials are used only for required provisioning interfaces.
- Bootstrap validation must prove that Keycloak claims resolve to Polaris principals and expected grants under the selected pinned versions.

## Role enforcement summary

| Role | Polaris/Iceberg behavior | Storage behavior |
|---|---|---|
| Developer | Read production/dev/UAT; write dev only | Polaris vends temporary credentials only for authorized Iceberg locations/operations; no direct S3 credentials |
| Analyst | Read production only; no writes | Polaris vending limited to authorized production reads; no direct S3 credentials |
| Owner | Manage product objects and product-scoped Polaris grants in all environments | Grant changes affect the data access Polaris will authorize and vend; direct RustFS policy administration remains platform-managed; no direct S3 credentials |
| Writer | Read/write all environments through approved workload | Polaris vends short-lived credentials for authorized table operations; no direct S3 credentials |

The platform admin can perform bootstrap provisioning but does not receive realm-admin or RustFS root privileges solely through product ownership.

## Error and recovery contract

Provider errors are returned with the failed stage, service name, and safe diagnostic context. Credential values, bearer tokens, and sensitive response bodies are redacted. The CLI returns failure if any required resource or smoke table cannot be verified. Existing partial state is retained so the ordered idempotent process can resume on rerun. Detailed error categories and timeouts are deferred to Functional/NFR Design.
