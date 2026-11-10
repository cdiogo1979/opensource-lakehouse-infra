# Application Design — StarRocks OSS Integration

This document consolidates the component, interface, service, and dependency design for adding StarRocks OSS to the existing Hive Metastore/Iceberg/RustFS lakehouse.

## Architectural Decisions

- Add a single StarRocks FE/BE runtime; keep Hive Metastore as the catalog, RustFS as object storage, and Spark/Jupyter as supported services.
- Separate StarRocks runtime, identity provisioning, and SQL bootstrap as logical components.
- Extend the existing identity provisioner for StarRocks-specific Kerberos and RustFS identities. StarRocks consumes mounted configuration and credential references.
- Use an explicit repeatable operator bootstrap command after FE readiness. Do not add a control-plane API or automatic long-running bootstrap service.
- Use StarRocks native SQL users/roles to enforce the approved matrix. Do not propagate end-user Kerberos identities through StarRocks.
- Keep host SQL/UI ports loopback-only, persist FE/BE state in named volumes, and preserve shared platform data and identities.

## Component Summary

| Component | Responsibility | Main interface |
|---|---|---|
| StarRocks Runtime | FE/BE services, SQL endpoint, health/readiness, persistent state | MySQL-compatible SQL protocol, Compose health and mounts |
| Identity Provisioning | StarRocks HMS Kerberos principal/keytab and scoped RustFS identity/policy | Existing provisioning commands and protected credential files |
| SQL Bootstrap | Iceberg catalog, native users/roles/grants | Explicit command orchestrating StarRocks SQL operations |
| Existing Shared Lakehouse Services | HMS, PostgreSQL, RustFS, KDC, Spark/Jupyter remain available | Existing Thrift, Kerberos, S3, and workload interfaces |
| SQL Clients and Operations | Submit SQL and operate local stack | Loopback SQL endpoint and documented Compose/CLI commands |

## Authorization Matrix

| StarRocks SQL identity | `databaseA` | `databaseB` | StarRocks administration |
|---|---|---|---|
| `user_a` | Read | Deny | No |
| `user_b` | Read | Read | No |
| `write_service_account` (maps from `write-service-account`) | Read/write | Read/write | No |
| `admin` | Full access | Full access | Full |

These SQL grants only govern access through StarRocks. Existing direct Spark/Hive/RustFS authorization remains separate.

## Service Lifecycle

The operator provisions StarRocks service identities through the existing identity provisioning boundary, starts FE/BE after shared dependencies are available, waits for readiness, and explicitly runs SQL bootstrap. Clients then connect through the loopback-bound SQL endpoint. Detailed catalog syntax, grant commands, ticket renewal, health-check implementation, and resource values are deferred to Construction design.

## Detailed Artifacts

- [Components](components.md)
- [Component Methods](component-methods.md)
- [Services](services.md)
- [Component Dependencies](component-dependency.md)

## Design Limits and Open Verification

- This is a local single-FE/single-BE PoC, not a production HA/security design.
- Verify the selected StarRocks release against Hive Metastore 3.1.3, secured HMS Kerberos, RustFS S3 compatibility, and current Iceberg table features.
- Verify StarRocks native grants constrain clients even though StarRocks' own service identity can access the warehouse.
- Test writes only against designated disposable or reversible data and confirm Spark interoperability.
