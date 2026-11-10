# Functional Design Plan — Unit 5 JupyterHub and Per-User Spark Access

## Scope

Adapt the existing `../jupyter-platform/` JupyterHub and single-user Spark setup to the Hive/Dremio/RustFS PoC in this workspace. Design isolated `user_a` and `user_b` notebook sessions that use their own provisioned Kerberos principals/keytabs and distinct RustFS identities, and demonstrate the approved Spark database access profiles. Retain DummyAuthenticator for local development only and document its authentication limitation. Include the operator `admin` identity only to the extent required by the approved Unit 5 stories.

This stage produces functional design artifacts only. It does not copy or modify runtime files, edit Compose, create credentials, start services, or run tests. Decisions that affect implementation are captured in the questions file before the design is finalized.

## Baseline Reviewed

- The sibling `../jupyter-platform/` contains JupyterHub 5.3.0, DockerSpawner, a Spark/Iceberg single-user image, and a separate Compose file connected to an external `iceberg-poc-net`.
- Its current Hub uses DummyAuthenticator, injects one shared hard-coded RustFS credential into every notebook, and its Spark catalog still points to Nessie.
- The target project already provisions distinct `user_a` and `user_b` Kerberos keytabs and RustFS identities. Its Hive Metastore, RustFS, and sample databases are available through the target Compose network.
- Approved Unit 5 stories are US-JH-01 and US-AUTH-03. The access profiles are `user_a` → `databaseA` only, and `user_b` → `databaseA` and `databaseB`.
- Canonical component design paths are `aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/jupyterhub.md` and the existing Spark component design `spark-runtime.md`; no Unit 5 canonical knowledge files are currently present.

## Design Checklist

- [x] Resolve the open integration, Spark execution, identity/admin, credential-delivery, and notebook-persistence decisions in `unit-5-functional-design-questions.md` (A/A/A/A/A).
- [x] Define the username-to-session and username-to-provisioned-identity mapping, including DummyAuthenticator's development-only boundary.
- [x] Model per-session Kerberos acquisition, ticket-cache isolation/lifecycle, Spark catalog access, and RustFS credential use.
- [x] Define the Spark allow/deny matrix and distinguish authorization failures from authentication, catalog, object-store, and session-start failures.
- [x] Specify notebook/session data flow, retained state, administrative behavior, and operator-visible outcomes.
- [x] Create the Unit 5 business logic, business rules, and domain entity artifacts under `construction/unit-5-jupyter/functional-design/`.
- [x] Update the workflow state and audit trail; present the design for explicit review before starting Unit 5 NFR Requirements.

## Questions and Approval

Answers were validated as A/A/A/A/A: integrate JupyterHub into this Compose project; run Spark locally in each isolated single-user container; allow `user_a`, `user_b`, and `admin` labels with `admin` mapped as a Hub administrator; mount the matching keytab read-only and inject only the matching RustFS credentials with a private ticket cache; and persist a separate per-user workspace without shared writable notebooks. The resulting design is ready for user review and explicit approval.
