# Functional Design Plan — Unit 2: Identity and Permission Provisioning

## Scope

This plan covers the approved one-shot identity/permission provisioner and its interactions with the existing KDC, Hive Metastore, metastore PostgreSQL, RustFS, Dremio, Spark, and the later JupyterHub unit. It defines functional workflows, ownership, permissions, repeat behavior, and failure handling. Concrete Compose services, scripts, APIs, image choices, mounts, and health checks belong to Infrastructure Design. No application configuration changes are made in this design stage.

Primary stories: US-ID-01 and US-ID-02. Related stories: US-AUTH-01, US-CAT-02, US-JH-01, US-ID-03, and US-JDBC-01.

## Approved scope and constraints

- Create distinct Kerberos principals for `admin`, `write-service-account`, `user_a`, and `user_b`; generate and protect their keytabs locally.
- Create component-native identities and credentials separately where Kerberos is not the component's authentication mechanism. Do not reuse Kerberos passwords/keytabs as web or S3 credentials.
- Create the `write-service-account` Dremio local user. Do not grant it Dremio platform administrator rights; its requested Space object-write capability is a feasibility gate for the Dremio-owned unit.
- Map `admin` to the administrative accounts/roles required by in-scope components while preserving component-specific credentials and setup mechanisms.
- Give the writer only the Hive and RustFS privileges needed to create and populate `databaseA` and `databaseB`. Do not give it PostgreSQL metastore access or platform-admin rights.
- Coordinate reader permission grants with the component that owns authorization. Database-specific grants may need to be applied after Unit 3 creates the databases.
- Keep secrets in ignored, local runtime credential files; redact credentials from command output and logs. Preserve credentials on safe reruns; rotations and destructive reset are explicit operator actions.
- The provisioner coordinates component-owned interfaces. It is not a runtime authorization engine, and this design must not claim that effective-user propagation or RustFS storage authorization works until verified.

## Functional Design Checklist

- [x] Review Unit 2's story map, approved requirements, Unit 1 contracts, and the existing runtime credential/bootstrap scripts.
- [x] Define the identity manifest: principal names, component account names, credential types, owners, and consumers.
- [x] Define idempotent principal/keytab creation and credential persistence/rotation behavior.
- [x] Define native account and permission setup responsibilities for KDC, Hive, PostgreSQL, RustFS, Dremio, Spark, and JupyterHub.
- [x] Define the minimum writer setup permissions and the later database-specific reader-grant sequence.
- [x] Define startup prerequisites, readiness, retries, partial failure, and safe rerun behavior.
- [x] Define secret redaction and local file access rules.
- [x] Generate Unit 2 functional design artifacts.
- [x] Validate the design against Unit 2 boundaries and the approved requirements.

## Answer Resolution

Answers 1, 3, 4, 5, and 6 are accepted as written. The initial answer 2/B was replaced by answer **A** in `unit-2-functional-design-clarification.md`, preserving the approved requirement for separate component-native administrator credentials. Kerberos, Dremio, RustFS, and PostgreSQL credentials remain distinct; writer and test-user credentials are distinct from administrator credentials.

## Design Questions

### Question 1 — Provisioner trigger and rerun contract

How should identity setup run against the local stack?

A) Add an explicit, idempotent one-shot provisioning step after required services are ready. It ensures each identity/account and reports created/already-present status; existing credentials are preserved unless the operator performs an explicit rotation/reset (recommended; safe for the persistent Compose volumes).

B) Create identities only during first-time Compose startup and require a full reset to change them.

X) Other (describe after `[Answer]:`)

[Answer]: A

### Question 2 — Component-native admin mappings

How should the `admin` principal map to the different components?

A) Keep one Kerberos `admin` principal but use separately generated component-native administrator credentials/roles for Dremio, RustFS, PostgreSQL, and any other component that does not authenticate with Kerberos. Do not assume a Kerberos principal alone creates a component administrator; document unsupported mappings as explicit gates (recommended; preserves credential separation).

B) Reuse one generated password across components for simpler local administration.

X) Other (describe after `[Answer]:`)

[Answer]: B

### Question 3 — Writer RustFS permissions

What storage scope should be assigned to `write-service-account`?

A) Create a distinct RustFS access key and a least-privilege policy limited to the `lake` bucket's warehouse prefixes needed for `databaseA` and `databaseB`; retain a separate setup/admin credential for provisioning (recommended; avoids using the bucket initializer's credentials for ETL).

B) Reuse the RustFS setup/admin access key for the writer in this local PoC.

X) Other (describe after `[Answer]:`)

[Answer]: A

### Question 4 — Hive permission and reader-grant timing

How should the provisioner handle database permissions before and after Unit 3 creates the sample databases?

A) Provision the writer's minimum pre-ETL capability through the selected Hive-owned mechanism; do not create databases or grant reader access in Unit 2. Provide a repeatable post-ETL grant step for `user_a`/`user_b` once the databases exist, and treat enforcement compatibility with Spark/Dremio/RustFS as a verification gate (recommended; respects component ownership and sequencing).

B) Have the provisioner create `databaseA`/`databaseB` and apply all reader grants before the ETL unit runs.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 5 — Dremio local identity setup boundary

How should Unit 2 handle Dremio local accounts before Unit 4 configures the Hive source and query mapping?

A) Ensure the `admin` and `write-service-account` local accounts through Dremio's supported setup interface once Dremio is initialized; leave source configuration, query-user mapping, and writer Space privilege feasibility to Unit 4. Do not elevate the writer if Community cannot grant the requested object-write access (recommended; respects component ownership).

B) Defer all Dremio local account creation to Unit 4.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 6 — Failure and partial provisioning

What should happen if one component account or permission cannot be provisioned?

A) Stop the one-shot provisioner at the failing component, report the component and safe diagnostic, preserve prior successful setup, and make rerun safe. Do not report identity setup as complete while any required mapping is missing (recommended; supports diagnosis without destructive rollback).

B) Continue all remaining setup and report a combined list of failures at the end.

X) Other (describe after `[Answer]:`)

[Answer]:A

## Feasibility gates

- Verify the selected Hive authorization mechanism can grant the writer's database/table operations and can later enforce the required reader allow/deny matrix for both Spark and Dremio. Do not equate Kerberos authentication with authorization.
- Verify RustFS supports distinct users and bucket/prefix-scoped policy for the selected image/version. Do not claim least privilege until the policy is exercised.
- Verify Dremio Community supports creating the required local users and determine whether the non-admin writer can create objects in an existing Space over JDBC. Any inability to meet the approved permission must be returned for review; do not silently grant administrator access.
- Keep PostgreSQL metastore credentials separate from platform admin and writer identities. The ETL writer receives no direct metastore database credentials.

## Extension Compliance Summary

- **Security Baseline**: Disabled by user choice. The approved credential separation, local-only scope, secret redaction, and least-privilege requirements remain mandatory design inputs.
- **Property-Based Testing (Partial)**: Reassess if functional design introduces a pure, testable transformation; no code or tests are introduced in this plan.
- **Resiliency Baseline**: Disabled by user choice. Safe retries, partial-failure reporting, and persistent-state preservation remain required functional behavior.

## Current Status

Unit 1 Build and Test is complete. The user directed continuation to Unit 2, so the Deploy handoff is deferred until the planned unit sequence is complete. The credential clarification is resolved as A. Unit 2 Functional Design artifacts are generated and ready for review. No application configuration has been changed.
