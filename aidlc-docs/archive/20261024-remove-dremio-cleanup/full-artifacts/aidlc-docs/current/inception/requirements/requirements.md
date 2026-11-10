# Requirements — Remove Dremio and Clean the Project

## Intent Analysis

- **User request:** Remove Dremio and clean unnecessary project contents.
- **Request type:** Refactoring and infrastructure cleanup.
- **Scope estimate:** Multiple components across Compose, Kerberos identity/configuration, Hive proxy configuration, TPCH tooling, bootstrap scripts, SQL examples, and documentation.
- **Complexity estimate:** Moderate. The cleanup must preserve the retained platform and local data while removing Dremio-only components and state.
- **Requirements depth:** Standard.

## Goal

Remove Dremio from the active project and its local runtime, and remove Dremio-only integration code and documentation. Keep the retained lakehouse PoC usable with Hive Metastore, PostgreSQL, Kerberos, RustFS, Spark, JupyterHub, and the TPCH Spark ETL.

## Functional Requirements

### FR-1 — Remove Dremio service and configuration

Remove the Dremio service, ports, image/build references, named data volume, secrets, and Dremio-only environment variables from the active Docker Compose and environment configuration. Retained services must continue to be represented in Compose.

### FR-2 — Remove Dremio integrations

Remove Dremio-only JDBC, Spaces/views, source-setup, and authorization-matrix integration code and examples. Preserve the TPCH Spark ETL that writes to the retained Hive/RustFS environment; remove only its Dremio JDBC phase and related driver dependencies.

### FR-3 — Remove Dremio Kerberos and proxy configuration

Stop provisioning and health-checking a Dremio Kerberos identity, remove Dremio-specific keytab handling and Hive `hadoop.proxyuser.dremio.*` properties, and remove the `dremio` principal from the existing KDC. Preserve all other Kerberos principals and KDC state.

### FR-4 — Remove Dremio-only local credentials and data

Remove Dremio-specific local password files and the Dremio keytab, and remove only Dremio's Docker container/data volume state. Do not reset or remove shared credentials, Hive/PostgreSQL metadata, RustFS objects, other principals, TPCH data/results, or Jupyter workspaces.

### FR-5 — Keep retained project capabilities

Keep Hive Metastore, PostgreSQL, Kerberos, RustFS, Spark, JupyterHub, and TPCH Spark ETL configuration and documentation. Update the active README and canonical project knowledge to describe the retained stack without Dremio. Preserve the archived previous intent and its records as historical artifacts.

### FR-6 — Make cleanup scoped and repeatable

Cleanup/provision/start scripts must no longer require Dremio credentials or start/build Dremio. Any operation that deletes runtime state must be narrowly scoped to explicitly authorized Dremio-only resources and must not remove retained service volumes or data.

## Non-Functional Requirements

### NFR-1 — Data preservation

Preserve the retained platform data and identities listed in FR-4. Do not use broad volume removal or whole-KDC resets as part of this cleanup.

### NFR-2 — Configuration consistency

Active Compose, scripts, environment examples, and current project documentation must not contain operational Dremio references that imply Dremio remains part of the supported stack. Historical archive material may retain references for provenance.

### NFR-3 — Verification scope

Verify changed pure helper functions and serialization round-trips with property-based tests only if such pure logic changes. PBT is not required for infrastructure-only edits. Security Baseline and Resiliency Baseline are disabled for this intent.

## Acceptance Criteria

1. The active Compose configuration contains no Dremio service, Dremio JDBC helper service, Dremio-only image, port, volume, or secret.
2. The retained Hive, PostgreSQL, Kerberos, RustFS, Spark, JupyterHub, and TPCH Spark ETL definitions remain present.
3. Active scripts and TPCH workload code no longer provision, start, connect to, or depend on Dremio.
4. The Dremio Kerberos principal and Dremio-only local password/keytab files are removed without changing other principals or credentials.
5. Only Dremio's container/data volume state is removed; retained named volumes and persisted data remain intact.
6. Active project documentation describes the retained stack; the prior intent archive remains unchanged.
7. Compose/configuration syntax and relevant changed helper behavior are verified as appropriate, and any unverified runtime cleanup is reported explicitly.

## Decisions and Constraints

- Retain Hive Metastore, PostgreSQL, Kerberos, RustFS, Spark, JupyterHub, and TPCH Spark ETL.
- Remove Dremio-only JDBC, Spaces/views, and related integration references.
- Remove Dremio-specific credentials, keytab, principal, and only Dremio Docker state.
- Preserve all other principals, shared credentials, metadata, objects, TPCH data/results, and notebook workspaces.
- Security Baseline: disabled.
- Property-Based Testing: partial; only changed pure functions and serialization round-trips.
- Resiliency Baseline: disabled.
- No Airflow/Jenkins additions are in scope.
