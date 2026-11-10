# Unit of Work Story Map — StarRocks OSS Integration

Each story has exactly one primary implementation unit. Cross-unit integration is verified after the three units are complete.

| Story | Capability | Primary unit | Requirement trace | Primary acceptance evidence |
|---|---|---|---|---|
| US-01 — Query the shared Iceberg lake | Catalog discovery and SQL queries over existing Iceberg data | Unit 3 — SQL Bootstrap and Catalog Access | FR-2, FR-3, FR-6 | `user_a` queries databaseA; `user_b` queries both databases; results are read from RustFS; unauthorized access is denied after catalog/storage health is established. |
| US-02 — Write Iceberg data as the ETL service account | Controlled StarRocks Iceberg writes | Unit 3 — SQL Bootstrap and Catalog Access | FR-3, FR-4, FR-6 | Writer can write/read back disposable or reversible test data in both databases; analyst identities cannot write; warehouse-scoped RustFS access is used. |
| US-03 — Restrict query access by StarRocks identity | Native SQL authorization | Unit 3 — SQL Bootstrap and Catalog Access | FR-6 | Full user matrix is demonstrated; writer is not a StarRocks administrator; grants are limited to StarRocks SQL access. |
| US-04 — Connect StarRocks using dedicated service credentials | HMS Kerberos and RustFS identity provisioning | Unit 1 — Identity Provisioning | FR-2, FR-4, FR-5, FR-6, NFR-1, NFR-2 | Dedicated StarRocks identities are separate, scoped, protected, redacted, repeatable, and do not rotate existing secrets. |
| US-05 — Run StarRocks in the local PoC | Single-node runtime, persistence, endpoint exposure, and operations | Unit 2 — StarRocks Runtime | FR-1, FR-7, NFR-1, NFR-2, NFR-3, NFR-4, NFR-5, NFR-6 | Pinned FE/BE stack has loopback-only endpoints, named volumes, readiness, documented local resources, and preserves existing services/data. |

## Cross-Story Integrated Verification

After Units 1–3, verify the combined acceptance path: secured HMS discovery, RustFS reads, controlled Iceberg write/readback, the complete SQL grant matrix, credential redaction, state persistence, Spark interoperability, and preservation of existing services/data. This activity does not create duplicate primary story assignments.
