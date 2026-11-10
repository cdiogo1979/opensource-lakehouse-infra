# Unit 2 Domain Entities — StarRocks Runtime

## StarRocksRuntime

Represents the local StarRocks deployment as one coordinated FE/BE pair.

| Attribute | Meaning |
|---|---|
| `runtime_state` | `UNINITIALIZED`, `STARTING`, `READY`, `CREDENTIAL_DEGRADED`, `NOT_READY`, or `STARTUP_BLOCKED` |
| `initialization_state` | `UNINITIALIZED`, `INITIALIZING`, `INITIALIZED`, or `INCONSISTENT` |
| `sql_endpoint` | Internal FE SQL service and its loopback-only host publication |
| `ui_endpoint` | FE web interface and its loopback-only host publication |
| `credential_state` | `VALID`, `REFRESH_DEGRADED`, or `EXPIRED_OR_UNAVAILABLE`; never contains credential values |

**Invariants:** one FE and one BE are members; `READY` requires both node health and FE SQL availability; runtime readiness does not claim external catalog readiness.

## FrontendNode

Represents the single StarRocks FE process.

| Attribute | Meaning |
|---|---|
| `health_state` | Node lifecycle/health reported by the runtime |
| `persistent_state` | FE data retained in its named volume |
| `sql_service_state` | Availability of FE SQL listener |
| `ui_service_state` | Availability of FE UI |

## BackendNode

Represents the single StarRocks BE process.

| Attribute | Meaning |
|---|---|
| `health_state` | Node lifecycle/health reported by the runtime |
| `persistent_state` | BE data retained in its named volume |
| `registered_with_frontend` | Whether the FE recognizes the BE as an available execution node |

## PersistentNodeState

Represents the data directory state for one FE or BE.

| Attribute | Meaning |
|---|---|
| `node_role` | `FE` or `BE` |
| `volume_state` | `EMPTY`, `INITIALIZED`, `MISSING`, `INVALID`, or `INCOMPATIBLE` |
| `last_known_runtime_version` | Version metadata needed to reason about compatibility; exact source is an implementation detail |

**Invariants:** FE and BE state are never interchanged; automatic initial setup is permitted only when both are empty and no completed-initialization guard exists; invalid or one-sided empty state after initialization blocks startup without modifying available data.

## ServiceCredentialSet

Represents the Unit 1 credential references consumed by StarRocks.

| Attribute | Meaning |
|---|---|
| `kerberos_principal` | `starrocks@<realm>` service principal reference |
| `keytab_reference` | Read-only path to Unit 1 keytab; does not hold keytab bytes in the domain model |
| `rustfs_access_key_id` | Stable RustFS identity identifier `starrocks` |
| `rustfs_secret_reference` | Read-only secret-file reference; does not hold the secret value |
| `credential_status` | Safe status enum only; no tokens, passwords, or secret data |

## KerberosTicketLifecycle

Represents the renewable/refreshed TGT state used by the StarRocks service identity.

| Attribute | Meaning |
|---|---|
| `ticket_state` | `VALID`, `REFRESH_DEGRADED`, or `EXPIRED` |
| `last_refresh_result` | Safe success/failure category without raw provider output |
| `next_refresh_at` | Refresh scheduling information; interval is selected in later design |

**Relationship:** `StarRocksRuntime` has exactly one `FrontendNode`, exactly one `BackendNode`, one `ServiceCredentialSet`, and one `KerberosTicketLifecycle`.

## Text Relationship Summary

- `StarRocksRuntime` coordinates one `FrontendNode` and one `BackendNode`.
- Each node owns a separate `PersistentNodeState`.
- The runtime consumes one `ServiceCredentialSet` and monitors one `KerberosTicketLifecycle`.
- The runtime validates both `PersistentNodeState` values together before initialization, preventing silent one-sided reinitialization.
