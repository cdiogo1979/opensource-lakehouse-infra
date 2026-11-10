# Tech-Stack Decisions — Hive Metastore and Direct Spark Authorization

## Approved constraints

| Area | Decision | Rationale / boundary |
|---|---|---|
| Hive Metastore | Retain the existing Hive 3.1.3 metastore and Kerberos SASL service path for Unit 3 verification. | The unit is an authorization validation step, not a service migration. Current configuration is not proof of per-user metadata enforcement. |
| Spark and Iceberg | Retain Spark 3.5.5 and Iceberg 1.8.1 with the existing HiveCatalog and S3FileIO setup. | Preserve the approved runtime while verifying direct HMS and RustFS behavior. |
| Object storage | Retain the current RustFS 1.0.0 image and existing three-bucket IAM design (`lake`, `lake-dev`, `lake-uat`). | RustFS policies are the object access boundary; no bucket or policy changes are authorized here. |
| Metadata visibility | Accept cross-environment database/table metadata visibility. Keep existing Hive settings unchanged for now; do not claim they provide per-user DDL authorization. | The required direct Spark data boundary is RustFS object authorization using role-specific credentials. Preventing analyst metadata DDL would need a separately approved HMS authorizer design. |
| Caller authentication | Preserve Kerberos SASL for HMS. Human Kerberos ticket provisioning and RustFS secret delivery remain distinct identity channels. | A valid ticket authenticates the HMS caller; it does not establish which S3 credentials the Spark S3 client uses. Unit 4 owns notebook credential delivery. |
| ETL identity | Keep `write-service-account` as the non-interactive ETL identity only. | Its broad bucket access must not become a human fallback. |
| Ranger | Do not add Ranger to the direct Spark/HMS/RustFS request path. | The approved design uses Ranger for supported StarRocks query authorization; it does not authorize direct S3A calls. |
| New authorization components | Add no plugin, gateway, HiveServer2, proxy, or new service in Unit 3 NFR Requirements. | Any new enforcement boundary needs pinned-version compatibility evidence and explicit architecture approval. If existing HMS behavior fails, stop and request that decision. |
| Network and transport | Keep the existing internal Compose endpoints and networks; no new published authorization ports or TLS termination service is selected. | Matches the local PoC answer. Existing HMS Kerberos SASL remains required; transport hardening changes need separate approval. |
| Logging and audit | Use bounded, sanitized application/container diagnostics; do not add a separate audit service or retention system. | Fixed PoC has no audit retention SLA; credential, ticket, request-body, and data-content redaction remains mandatory. |
| Test environment | Use disposable database/table/object state and test identities; never use production objects for negative probes. | Allows verification and recovery testing without risking existing production data. |

## Deferred decisions and verification gates

- Whether analysts must also be prevented from Hive metadata DDL (create/alter/drop); current scope does not guarantee those denials.
- Exact principal HMS sees for each Spark client operation and how that identity is mapped by the server-side authenticator.
- Effective permission/cache behavior and measured revocation delay across FreeIPA membership, Kerberos tickets, HMS, Spark, Iceberg, and RustFS.
- Exact timeout and retry settings after dependency behavior is measured; no latency SLA was selected.
- An HMS metadata authorizer if analyst DDL restrictions become a requirement. This must return for architecture review; it cannot be inferred or selected here.

## Change control

Any version change, new authorization service/plugin/gateway, added HiveServer2, new host-published port, role-scope change, credential fallback, or production database relocation requires a separate review and approval. Cross-environment metadata visibility is accepted by the user; it does not waive the independent RustFS data-access matrix.
