# Unit of Work Definitions — StarRocks OSS Integration

## Decomposition Principles

- Keep units aligned to the approved Identity Provisioning, StarRocks Runtime, and SQL Bootstrap components.
- Follow the approved sequential order with one operator/developer owning all units.
- FE and BE form one local deployment and remain in the same unit.
- Catalog registration and native StarRocks user/role/grant setup remain together.
- Add setup and validation documentation within each unit. Run integrated end-to-end verification after all units; it is not a fourth implementation unit.
- Preserve all existing services, credentials, Hive metadata, RustFS data, and notebook workspaces. Do not modify the sibling Airflow/Jenkins project.

## Unit 1 — Identity Provisioning

**Purpose:** Provide StarRocks-only service credentials for secured HMS and scoped RustFS access, using the existing identity-provisioning boundary.

**Responsibilities:**

- Create or reuse a dedicated StarRocks Kerberos service principal/keytab for HMS access.
- Create or reuse a separate RustFS identity/policy with read/write limited to the Iceberg warehouse prefix.
- Keep keytabs and generated credentials in ignored protected runtime files and redact values from output.
- Preserve existing credentials and identities; no implicit rotation.
- Document the provisioning operation, inputs, protected outputs, and verification steps.

**Primary requirement ownership:** FR-4, FR-5, NFR-1 (identity secret handling), NFR-2 (idempotency and no implicit rotation).

**Primary story ownership:** US-04.

**Canonical design ownership:** `aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/starrocks-analytics.md`; shared identity interaction belongs in `functional-design/lakehouse-workload-and-access.md`.

**Completion boundary:** StarRocks-only identity references and policies are provisioned and documented. Runtime consumption and catalog connectivity belong to later units.

## Unit 2 — StarRocks Runtime

**Purpose:** Add a persistent local StarRocks OSS deployment using one FE and one BE.

**Responsibilities:**

- Select and pin a reviewed stable StarRocks OSS image/version and document local resources.
- Define FE/BE Compose services, internal networking, readiness/health behavior, configuration mounts, and named volumes.
- Bind host SQL and FE UI ports to loopback only.
- Consume Unit 1's mounted credential/configuration contract without placing secret values in tracked files or logs.
- Preserve existing Compose services, mounts, and named volumes.
- Document startup, readiness, endpoints, resources, persistence, and safe stop/recreate operations.

**Primary requirement ownership:** FR-1, FR-7 (Compose/service preservation), NFR-1 (endpoint exposure and runtime secret handling), NFR-3, NFR-4 (image/runtime compatibility), NFR-5, and NFR-6 (runtime operations documentation).

**Primary story ownership:** US-05.

**Canonical design ownership:** `aidlc-docs/knowledge/hive-dremio-rustfs/application-design.md` for project boundaries and `functional-design/starrocks-analytics.md` for StarRocks runtime behavior.

**Completion boundary:** FE and BE can start and report readiness with persistent state and correct local exposure. External catalog setup and user grants belong to Unit 3.

## Unit 3 — SQL Bootstrap and Catalog Access

**Purpose:** Configure StarRocks to use the existing secured HMS Iceberg catalog and RustFS warehouse, then apply native SQL authorization.

**Responsibilities:**

- Provide an explicit, repeatable bootstrap command that waits for Unit 2 FE readiness.
- Configure/reconcile the Iceberg catalog using the Unit 1 Kerberos and RustFS credential contract.
- Provision StarRocks native SQL users/roles and access grants, mapping `write-service-account` to `write_service_account` if required.
- Enforce `user_a` read access to databaseA only; `user_b` read access to both; writer read/write access to both without StarRocks administration; and `admin` full StarRocks access.
- Keep catalog setup and SQL authorization together, as both are configured through StarRocks SQL after FE readiness.
- Document bootstrap inputs, safe reruns, SQL connectivity, and grant behavior.

**Primary requirement ownership:** FR-2, FR-3, FR-6, NFR-1 (SQL credential handling), NFR-2 (repeatable bootstrap), and FR-7 (catalog/table preservation during setup).

**Primary story ownership:** US-01, US-02, and US-03.

**Canonical design ownership:** `aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/starrocks-analytics.md` and `functional-design/lakehouse-workload-and-access.md` for shared-engine workload/access behavior.

**Completion boundary:** The external catalog is accessible and native SQL grants are applied. End-to-end verification must still demonstrate allowed and denied queries, a controlled write/readback, and preservation of shared services/data.

## Integrated Verification After Units 1–3

This is a final cross-unit activity, not a separate implementation unit. It verifies Compose/readiness, secured HMS catalog discovery, RustFS reads, controlled Iceberg write/readback, the full SQL access matrix, credential redaction, persistence, Spark interoperability, and preservation of existing platform data. Any unverified criterion must be reported clearly; no successful status is inferred from generated artifacts alone.
