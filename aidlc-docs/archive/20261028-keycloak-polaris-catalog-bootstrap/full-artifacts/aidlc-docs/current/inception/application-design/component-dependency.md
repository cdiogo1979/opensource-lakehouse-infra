# Component Dependencies and Data Flow

## Dependency matrix

| Caller | Depends on | Interface/pattern |
|---|---|---|
| Platform Admin CLI | Bootstrap Coordinator, Credential Source, Readiness/Report Builder | In-process calls; protected secret handles |
| Bootstrap Coordinator | Keycloak, Polaris, RustFS adapters; Spark Job Runner | Ordered adapter calls; structured step results |
| Keycloak Adapter | Keycloak Admin API and OIDC metadata | HTTPS management API and OIDC discovery/JWKS |
| Polaris Adapter | Polaris Management API and Iceberg REST API | HTTPS REST; OAuth/OIDC bearer tokens |
| RustFS Adapter | RustFS S3/admin interfaces | S3-compatible/admin API over internal Compose network |
| Spark Job Runner | Spark image/runtime, Keycloak token endpoint, Polaris Iceberg REST, RustFS through vended credentials | Short-lived container; OAuth + Iceberg REST + S3-compatible client |
| Polaris | PostgreSQL; RustFS as configured storage integration | JDBC for metadata; S3-compatible operations and credential vending |
| Smoke Job | Polaris catalogs/namespaces and vended credentials | Iceberg REST table APIs and S3 data I/O |

## Bootstrap sequence

```mermaid
sequenceDiagram
  actor Operator as Platform Administrator
  participant CLI as Bootstrap CLI
  participant KC as Keycloak Adapter/API
  participant RFS as RustFS Adapter/API
  participant POL as Polaris Adapter/API
  participant SP as Spark Smoke Job
  participant PG as Polaris PostgreSQL
  Operator->>CLI: bootstrap default
  CLI->>KC: ensure groups, writer client, owner membership
  KC-->>CLI: identity resources validated
  CLI->>RFS: ensure three buckets and storage setup
  RFS-->>CLI: bucket state validated
  CLI->>POL: ensure catalogs, namespaces, principals, roles, grants
  POL->>PG: persist Polaris metadata
  PG-->>POL: metadata committed
  POL-->>CLI: catalog and grants ready
  CLI->>SP: launch writer-authenticated smoke job
  SP->>KC: obtain OAuth token
  KC-->>SP: access token with mapped role claim
  SP->>POL: create/read smoke tables via Iceberg REST; request vended credentials
  POL->>PG: authorize principal and resolve grants
  PG-->>POL: authorization result
  POL-->>SP: table metadata and scoped short-lived storage credentials
  SP->>RFS: read/write Iceberg objects at matching environment paths
  RFS-->>SP: object operation result
  SP-->>CLI: per-environment smoke result
  CLI-->>Operator: redacted bootstrap report
```

## Trust boundaries

1. **Operator/runtime secret boundary:** bootstrap credentials and writer OAuth client secret enter through protected runtime files/secrets; only adapters receive the minimum needed handles.
2. **Identity boundary:** Keycloak signs human/service tokens. Polaris validates the configured issuer/audience and maps allowed claims to Polaris principal roles.
3. **Catalog authorization boundary:** Polaris RBAC authorizes catalog, namespace, and table actions before returning Iceberg metadata or vended credentials.
4. **Object storage boundary:** users do not receive static S3 keys. Vended short-lived credentials scope storage operations for authorized Iceberg locations. Bucket and location isolation remains a RustFS/Polaris integration test requirement.
5. **Container network boundary:** internal service DNS is used by containers; external loopback endpoints are only for operator interfaces and host CLI access as defined in Infrastructure Design.

## Dependency constraints and validation

- Keycloak claim path, role transformation, and Polaris principal lookup must be tested against the selected Polaris release.
- Polaris must be configured with RustFS endpoint, path-style behavior, region, storage role/STS or supported equivalent, and delegation enabled as required by the selected RustFS release.
- Polaris role authorization and credential vending must both enforce environment scope; successful catalog authorization alone is not evidence of correct S3 isolation.
- Spark must use compatible Polaris/Iceberg client artifacts and include the vended-credentials request behavior.
- The platform-admin bucket-provisioning credential is distinct from Polaris’s runtime storage credential and from writer credentials.
- No direct user S3 keys are issued; a raw S3 request without a Polaris-vended credential is expected to fail.
