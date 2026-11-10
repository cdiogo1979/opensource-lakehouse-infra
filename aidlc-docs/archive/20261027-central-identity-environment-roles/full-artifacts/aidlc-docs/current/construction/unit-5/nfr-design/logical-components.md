# Unit 5 NFR Design — Logical Components

| Component | Responsibility | Boundary |
|---|---|---|
| FreeIPA | Authenticate users and maintain canonical role groups | LDAPS only; directory administrator is not used as the StarRocks lookup identity |
| StarRocks LDAP authentication | Validate registered SQL user credentials against FreeIPA | Each SQL principal is registered with its FreeIPA DN; no local password fallback |
| StarRocks LDAP Group Provider | Resolve FreeIPA groups for authenticated users | Read-only bind, LDAPS, explicit group filter/member attribute, bounded cache |
| StarRocks native RBAC | Map external groups to roles and enforce resource/action grants | Explicit Iceberg source lists and internal MV databases; writer has only scoped MV management, no general DDL/security grants |
| StarRocks FE/BE service identity | Access HMS and RustFS after native SQL authorization | Separate from user identity; protected Kerberos and S3 credentials |
| RustFS IAM | Enforce S3 permissions for direct Spark users and StarRocks backend | Independent policy path; StarRocks role does not grant raw S3 access |
| Bootstrap utility | Reconcile group provider, LDAP user registrations, roles, grants, and group mappings | Exact disposable test FE guard; protected secrets; sanitized errors |

## Request path

```text
SQL user ── LDAP bind ──> FreeIPA
    │
    ├── Group Provider query ──> FreeIPA role groups
    │                               │
    │                               v
    │                    external group → StarRocks role
    │                               │
    └──────── query ────────────────v
                         StarRocks native RBAC
                               │ allow
                               v
                StarRocks FE/BE identity → HMS / RustFS

Spark user → RustFS directly under that user's own RustFS policy
```

## Failure boundaries

| Failure | Behavior |
|---|---|
| LDAP login failure or invalid TLS | Reject login |
| User unregistered in StarRocks | Reject login |
| No recognized external group | Grant no data role |
| LDAP group service unavailable | Do not add a role; measured cached groups may remain until expiry |
| No table/database grant | StarRocks denies query before backend results are returned |
| HMS/RustFS backend failure | Query fails under the StarRocks service identity |
| Audit/diagnostic failure | Do not convert a denial or indeterminate authorization into allow |
| Direct Spark object access | RustFS decides independently of StarRocks |
