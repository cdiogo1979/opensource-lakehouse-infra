# Component Dependencies — StarRocks OSS Integration

## Dependency Matrix

| Consumer | Provider | Interface | Dependency purpose |
|---|---|---|---|
| StarRocks Runtime | KDC / identity provisioning | Mounted Kerberos config and keytab reference | Obtain/refresh the StarRocks service TGT for secured HMS access. |
| StarRocks Runtime | RustFS / identity provisioning | S3-compatible endpoint and mounted credential references | Read and write Iceberg objects within the approved warehouse prefix. |
| StarRocks Runtime | Hive Metastore | HMS Thrift and Iceberg catalog integration | Discover namespaces/tables and read/write Iceberg metadata. |
| StarRocks Runtime | Compose network and persistent volumes | Internal service DNS, health state, named volumes | FE/BE coordination, service readiness, and durable local state. |
| Identity Provisioning | KDC | Existing principal/keytab provisioning mechanism | Create or reuse the StarRocks HMS service identity. |
| Identity Provisioning | RustFS | Existing administrative identity/policy mechanism | Create or reuse the StarRocks warehouse-scoped service identity. |
| SQL Bootstrap | StarRocks FE | StarRocks SQL protocol using bootstrap admin credentials | Configure the Iceberg catalog and reconcile native SQL accounts/grants. |
| SQL Bootstrap | Identity Provisioning | Mounted files/environment contract and credential references | Access service configuration without placing literal secrets in tracked files. |
| SQL Clients | StarRocks FE | MySQL-compatible SQL protocol on loopback host port | Submit queries and writes under native StarRocks SQL authorization. |
| Spark/Jupyter | Existing HMS, RustFS, KDC | Existing configured interfaces | Continue existing workload behavior, independent of StarRocks bootstrap. |

## Data and Control Flow

### Startup and setup control flow

1. The operator requests identity provisioning; the existing provisioner interacts with KDC and RustFS and stores StarRocks-only credential material in the protected runtime location.
2. Compose starts StarRocks FE/BE after existing shared services are available; mounted identity/configuration lets the runtime reach KDC, HMS, and RustFS.
3. The operator waits for FE health, then runs the SQL bootstrap command.
4. SQL bootstrap connects to FE and configures the external Iceberg catalog and native StarRocks SQL users/roles/grants.
5. SQL users connect to the FE SQL endpoint and query or write through StarRocks.

### Query and write data flow

1. A client authenticates to StarRocks with a native SQL account.
2. StarRocks checks that account's catalog/database/table privileges.
3. The StarRocks service authenticates to HMS using its dedicated Kerberos identity to resolve Iceberg metadata.
4. StarRocks reads or writes object data in RustFS using its dedicated scoped S3 identity.
5. Iceberg commits are coordinated through the catalog/storage integration; Spark continues to use its existing independent identity and configuration.

The StarRocks service identity is shared by requests reaching HMS/RustFS; client-level authorization is enforced by StarRocks native SQL privileges. This design does not claim end-user Kerberos or S3 impersonation.

## Dependency Constraints

- Do not alter Hive metadata, existing RustFS data, or current Spark/Jupyter identities as part of StarRocks setup.
- Keep service names and endpoints internal to Compose except loopback-published SQL/UI endpoints.
- Bootstrap depends on FE readiness and provisioned credential references; a healthy container alone does not prove catalog connectivity.
- Exact Kerberos renewal, S3 connector settings, Iceberg feature compatibility, and rollback behavior require Construction NFR/Infrastructure/Functional design and runtime verification.
