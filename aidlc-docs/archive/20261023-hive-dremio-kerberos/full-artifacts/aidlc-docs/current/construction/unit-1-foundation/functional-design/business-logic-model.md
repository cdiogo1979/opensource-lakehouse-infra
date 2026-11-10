# Unit 1 Functional Design — Business Logic Model

## Purpose

Define the logical lifecycle for the Compose, catalog, identity foundation, and storage unit. The model covers a repeatable local foundation without prescribing Docker image configuration or implementation commands.

## Actors and Responsibilities

| Actor/component | Functional responsibility |
|---|---|
| Operator | Starts, stops, inspects, or explicitly resets the local PoC. |
| Compose lifecycle | Orders foundation startup and dependent initialization; stops dependent work after a required failure. |
| Kerberos KDC | Owns the disposable realm and creation/authentication of required principals and keytabs. |
| Metastore PostgreSQL | Persists Hive catalog metadata; it is not the authorization policy store for object data. |
| Hive Metastore | Owns Hive catalog metadata lookup and its configured metastore authorization checks. |
| RustFS | Owns bucket/object storage and native S3-compatible credential/policy behavior. |
| Bucket initializer | Ensures the baseline bucket exists without deleting existing objects. |
| Unit 2 identity provisioner | Coordinates principals, users, and grants using component-owned interfaces; not a runtime authorization decision point. |
| Unit 3 ETL | Creates the sample databases/tables as `write-service-account` after required foundation readiness. |

## Foundation Lifecycle

### Fresh startup

1. Validate that required local configuration and runtime credential inputs are available without logging secret values.
2. Start the KDC, Hive metadata PostgreSQL, and RustFS foundations.
3. Initialize KDC identities and the Hive metadata schema through their owning services.
4. Ensure the `lake` bucket exists; preserve any existing objects.
5. Start Hive Metastore after schema, KDC service identity, and storage configuration are ready.
6. Hand off to Unit 2 for component identity/permission provisioning.
7. Hand off to Unit 3 only after required writer credentials/permissions and Hive/RustFS readiness are confirmed.

The exact interleaving of KDC and database startup is an infrastructure detail, but Hive Metastore must not be reported ready before its required schema and service authentication prerequisites are complete.

### Existing deployment rerun

1. Detect persisted catalog and bucket state.
2. Ensure missing baseline resources without dropping or replacing existing catalog records or objects.
3. Report resources that already exist and preserve their data.
4. If persisted state conflicts with the selected service/catalog contract and cannot be safely reconciled, stop with a clear diagnostic and preserve the state for inspection.

Repeatability means a clean deployment can be initialized and a non-destructive rerun does not erase existing data. It does not authorize silently changing table contents, deleting metadata, or rotating credentials in a way that invalidates existing state.

## Catalog and Storage Data Flow

1. Unit 3's Spark loader creates `databaseA` and `databaseB` metadata in Hive Metastore as `write-service-account`.
2. Hive database and table locations refer to RustFS warehouse paths.
3. Spark writes Iceberg metadata/data objects to RustFS using the writer's scoped credentials.
4. Dremio and notebook Spark query paths resolve catalog metadata through Hive Metastore and access table data through their respective configured storage paths.
5. Unit 2 coordinates reader permissions after databases are created. The actual allow/deny decision remains in component-owned authorization checks.

## Authorization Evaluation Model

The selected baseline remains standalone Hive Metastore without HiveServer2. Metastore storage-based authorization is the mechanism to evaluate for metadata API calls. Apache Hive describes this mechanism as using permissions on the underlying database/table paths; this behavior has not been demonstrated for RustFS or for both Dremio and Spark effective identities.

For each query path, the intended logical check is:

1. Establish the authenticated/effective user (`user_a` or `user_b`).
2. Resolve the requested Hive database/table metadata.
3. Apply Hive Metastore authorization using the effective user's access to the associated storage resource.
4. Allow metadata resolution only when the selected mechanism validates the required path permission; otherwise return an authorization denial.
5. Record which effective identity and outcome were observed without exposing credentials.

If the selected Metastore/RustFS combination cannot evaluate the effective user and produce the required database outcomes, the result is a feasibility blocker. Do not report authorization success based only on hidden Dremio source credentials or a shared storage administrator identity. Any architecture change, including adding a query authorization service or changing the no-HiveServer2 boundary, must be returned for approval.

Hive SQL-standard authorization is documented as a HiveServer2 query authorization mode. Since Dremio's selected path is through Hive Metastore and Spark also uses the metastore, adding HiveServer2 alone must not be assumed to govern both paths.

## Failure and Recovery Flow

- A required KDC, schema, bucket, or Hive initialization failure marks the dependent startup chain failed.
- Dependent ETL and query initialization do not continue under a partial or unknown authorization state.
- Independent infrastructure may remain available for diagnosis, but no downstream component is presented as ready for acceptance.
- Persistent volumes and generated state remain available after failure for inspection.
- Recovery reruns must preserve existing data and report already initialized resources; the explicit full reset is a separate operator action.

## Stop and Reset Lifecycle

- Stop-only lifecycle stops containers/services and preserves named catalog and object-store volumes.
- Full reset is an explicit destructive operator action that removes named volumes and therefore Hive metadata and RustFS objects. It must be clearly identified before execution.
- No startup or error-recovery path automatically invokes full reset.

## Evidence and Unresolved Feasibility

- Hive documents that Metastore storage-based authorization checks database/table path permissions and metadata reads: [Hive Metastore Storage-Based Authorization](https://cwiki.apache.org/confluence/display/hive/storage%2Bbased%2Bauthorization%2Bin%2Bthe%2Bmetastore%2Bserver).
- Hive documents SQL-standard authorization as HiveServer2-based and describes client restrictions needed to prevent bypass: [Hive Authorization](https://cwiki.apache.org/confluence/display/Hive/LanguageManual+Authorization), [SQL Standard Based Hive Authorization](https://cwiki.apache.org/confluence/display/Hive/SQL%2BStandard%2BBased%2BHive%2BAuthorization).
- RustFS path-level authorization semantics, Hive effective-user propagation, and Dremio behavior remain to be verified during later infrastructure/integration planning. This document does not claim the authorization acceptance criteria have passed.
