# Unit 2 Identity Provisioning — Technology Stack Decisions

## Decisions

| Area | Decision | Rationale and status |
|---|---|---|
| Provisioning model | Use an explicit idempotent one-shot operator action after required services are ready. | Approved functional design; exact Compose service/command shape belongs to Infrastructure Design. No persistent identity-management service is added. |
| Kerberos | Extend the existing disposable MIT KDC realm and preserve the Hive Metastore service principal. | Unit 1 already owns the KDC lifecycle. Unit 2 adds `admin`, `write-service-account`, `user_a`, and `user_b` as separate principals with separate keytabs. |
| Credential storage | Use the existing ignored `.runtime/credentials/` boundary for local generated material. | Matches the Unit 1 bootstrap contract. Exact file layout, host modes, and mounts are defined in Infrastructure Design. |
| Native component accounts | Use each pinned component's supported account/role/policy interface. | Dremio, RustFS, and PostgreSQL do not share one credential authority. Each component admin credential is separately generated; no new shared identity service is introduced. |
| RustFS writer identity | Create a distinct RustFS access key and a least-privilege policy for required warehouse prefixes, separate from bucket setup/admin credentials. | Required by FR-23 and approved Unit 2 decisions. Exact policy/API capability must be verified against the pinned RustFS image. |
| Hive permissions | Configure requested permissions through Hive/Hadoop's component-owned authorization mechanism; do not add HiveServer2 or another policy service without review. | Preserves the approved standalone Metastore scope. The ability to enforce writer and reader rules over RustFS remains a feasibility gate. |
| Dremio users | Create the Dremio local admin and writer users after Dremio initial setup through a supported interface. | Unit 2 owns these accounts; Hive source setup, query-user mappings, and non-admin Space object-write feasibility belong to Unit 4. |
| PostgreSQL roles | Keep the Hive Metastore `hive` role and its secret separate from the native PostgreSQL administrator role. | The writer receives no direct metastore database credential. Admin setup remains component-native. |
| Spark/Jupyter identity | Spark consumes Kerberos and RustFS credentials; JupyterHub identity/session mapping is implemented by Unit 5. | Spark has no separate identity directory in scope. This decision avoids inventing an account model. |
| Reporting | Emit concise per-component/per-identity statuses and redacted errors to the operator. | No new report store, monitoring service, or UI is required for the single-maintainer local PoC. |
| Version policy | Preserve the Unit 1 pins unless a required native account/policy interface is unsupported. | Any version change, credential sharing, or privilege broadening is returned for review before implementation. |

## Compatibility Evidence and Validation Boundary

The exact account-management interfaces for Dremio Community 26.0.5, RustFS 1.0.0-glibc, and PostgreSQL 16.14 must be validated during Infrastructure Design and Code Generation. This document selects the component-owned-interface pattern but does not assert API availability or successful provisioning.

The following remain explicit verification gates:

1. RustFS supports distinct administrator, writer, and test-user credentials with the required bucket/prefix policy semantics.
2. The standalone Hive Metastore configuration can express the writer's database/table setup permissions and later reader grants for Spark and Dremio over RustFS.
3. Dremio Community can create the local admin and writer users and may permit the non-admin writer's required Space object creation over JDBC. The writer must not be elevated to administrator if this is unsupported.
4. Native administrator mappings exist for components included in the approved admin story. Where a component has no user-account model, an operator access procedure is documented instead of claiming an account was created.
5. Existing component startup and health dependencies provide a reliable gate before the one-shot provisioner mutates state.

If a gate fails, document the observed behavior and smallest proposed change for user review. Do not change image versions, add a runtime service, or broaden permissions solely to make the setup report green.

## Deferred Infrastructure Decisions

1. Whether to implement the one-shot provisioner as a Compose one-off service, script, or both.
2. Component-specific account creation commands/API calls and readiness probes.
3. Exact local runtime file names, permission modes, and consumer-specific read-only mounts.
4. RustFS policy document/actions and tested prefix boundaries.
5. How the post-ETL reader-grant operation is invoked after Unit 3 creates the databases.
6. Whether and how Unit 2's explicit provisioning operation integrates into the existing `scripts/start.sh` workflow without causing unintended first-run Dremio setup.

These are Infrastructure Design/Code Generation decisions and do not alter approved functional or NFR requirements.
