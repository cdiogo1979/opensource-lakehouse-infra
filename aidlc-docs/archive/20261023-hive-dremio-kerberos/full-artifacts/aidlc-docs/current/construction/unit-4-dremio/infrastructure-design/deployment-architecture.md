# Unit 4 Deployment Architecture — Dremio Source and Query Identity

## Existing service path

The operator connects to the existing Dremio Community 26.0.5 UI or JDBC endpoint as `user_a` or `user_b`. Dremio authenticates to Hive Metastore 3.1.3 with its Kerberos service identity and forwards the query username for impersonation. Hive Metastore uses PostgreSQL for catalog metadata and RustFS for the warehouse objects. Dremio's Hive source uses the existing shared RustFS writer credential. Unit 4 adds no Compose service, port, volume, or network. User-specific RustFS authorization is not implied by that shared source credential.

## Dependencies and preserved state

| Existing component | Dependency or path | Unit 4 treatment |
|---|---|---|
| Dremio | KDC, Hive Metastore, RustFS | Reuse current container/source and named data volume; local user accounts are distinct. |
| Hive Metastore | PostgreSQL metadata DB, KDC, RustFS warehouse | Reuse current service and metadata/configuration; authorization listener/provider configuration must be verified before allow/deny results count. |
| PostgreSQL | Persistent Hive metastore schema | Preserve `metastore-db-data`; no schema reset. |
| KDC | Persistent principal database and runtime keytabs | Preserve `kerberos-kdc-data` and existing service identities/keytabs. |
| RustFS | Persistent bucket/object data | Preserve `object-store-data` and current writer key. |
| Spark | Existing service and sample dataset | No Unit 4 change or ETL rerun. |

## Operator sequence

1. Confirm the existing Compose services and manually configured Hive source are available.
2. Authenticate to Dremio separately as `user_a` and `user_b` using distinct local Dremio credentials.
3. Execute the four direct Hive-source database checks serially and capture effective identity plus allow/deny result. Use the Space views only as supplemental checks.
4. Classify errors by Dremio authentication, source/Space permissions, Hive impersonation/authorization, missing object, or RustFS/S3 credential path.
5. Store only redacted local evidence. Preserve all named volumes and data; after diagnosis, rerun only failed non-destructive checks.

## Exposure and recovery boundaries

- Existing Dremio, Spark, and RustFS host ports remain bound to loopback. No new host port or public endpoint is introduced.
- Inter-service traffic stays on the existing private Compose network.
- Recovery is manual and fail-closed. No automatic retry, failover, volume reset, destructive cleanup, or admin fallback is part of the verification sequence.
- Dremio passwords, Kerberos keytabs/tickets, RustFS keys, and authorization headers are never included in query evidence or logs retained for review.
