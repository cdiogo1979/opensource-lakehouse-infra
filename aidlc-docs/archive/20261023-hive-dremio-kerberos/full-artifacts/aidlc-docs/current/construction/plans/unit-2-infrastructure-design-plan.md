# Infrastructure Design Plan — Unit 2 Identity and Permission Provisioning

## Scope

Map Unit 2's approved identity/permission workflow to concrete deployment boundaries in the existing single-host Compose project: the one-shot provisioner, KDC principal/keytab operations, Dremio local accounts, RustFS users/policies, PostgreSQL administrator role, Hive authorization integration, credential mounts, and dependency/readiness contracts. Do not implement the service or modify Compose in this stage.

Unit 2 does not create sample databases or tables, configure Dremio's Hive source, configure JupyterHub user sessions, or add Airflow/Jenkins. Those remain Units 3–5 or deferred scope. Do not add a persistent identity store, policy engine, monitoring stack, or external identity provider.

## Infrastructure Category Applicability

| Category | Applicability and evidence |
|---|---|
| Deployment environment | Applicable. The approved target remains the existing local Docker Compose deployment on one developer host; no additional environment is in scope. |
| Compute infrastructure | Applicable. Decide how the one-shot provisioner runs, its base image/runtime, and how it uses component-specific interfaces. No persistent identity service or replicas are allowed by approved design. |
| Storage infrastructure | Applicable. Map credential inputs/outputs to the ignored, restricted `.runtime/credentials/` directory; do not add another account database or volume. Component-owned account state remains in KDC, RustFS, Dremio, and PostgreSQL. |
| Messaging infrastructure | Not applicable. Setup is a sequential operator-triggered workflow with no asynchronous queue or event bus. |
| Networking infrastructure | Applicable. Provisioner-to-component traffic uses the private Compose network; do not publish provisioner ports or add LAN exposure. |
| Monitoring infrastructure | Not applicable as a new component. Compose status and concise secret-safe command/log output are sufficient. |
| Shared infrastructure | Not applicable. The PoC remains a single local Compose project with no shared identity platform or cross-environment credential store. |

## Infrastructure Design Checklist

- [x] Confirm the one-shot execution boundary and ensure it does not run as an unintended default startup side effect.
- [x] Map component readiness dependencies and exact ordering before provisioning mutations.
- [x] Define runtime image/tooling responsibilities for component-specific adapters.
- [x] Define local credential generation, read-only inputs, restricted outputs, and ownership boundaries.
- [x] Define internal network access and confirm no provisioner host ports are needed.
- [x] Define component account/policy state ownership, safe reruns, and explicit credential rotation behavior.
- [x] Record API/version and Hive/RustFS permission feasibility gates.
- [x] Confirm messaging, monitoring, and shared-infrastructure exclusions with rationale.
- [x] Generate Unit 2 infrastructure design and deployment architecture artifacts.
- [x] Validate against approved Functional Design, NFR Requirements, and NFR Design.

## Design Questions

### Question 1 — One-shot provisioner execution model

How should the provisioner be launched in Compose?

A) Use a project-owned one-shot Compose service/image, invoked explicitly by the operator after the core stack is ready. Keep it out of the default `up` path; connect it only to required service dependencies and remove its container after completion (recommended; gives component tools a consistent private-network environment without adding a persistent service).

B) Use a host-side script that calls the component CLIs/APIs directly; do not add a provisioner image or Compose service.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 2 — Credential generation and file ownership

Where should native passwords, access keys, and keytabs be generated and stored?

A) Generate/provision secrets through the existing local bootstrap and component-owned setup flows into the ignored, host-restricted `.runtime/credentials/` tree. The provisioner reads only required admin inputs and writes generated artifacts with restrictive modes; never print values or store credentials in its image/container layer (recommended; reuses Unit 1's credential boundary).

B) Store generated credential files inside a dedicated persistent Compose volume.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 3 — Service readiness and Dremio initialization

How should provisioning handle dependencies that require operator setup?

A) Gate on health for KDC, PostgreSQL, Hive, and RustFS, plus successful bucket initialization. Require Dremio's first-run local administrator setup to be completed before its account adapter runs; fail with a clear prerequisite message rather than attempting unattended bootstrap (recommended; avoids assuming undocumented first-run behavior).

B) Have the provisioner perform Dremio's first-run setup automatically as part of Compose startup.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 4 — Native account interface ownership

How should component setup interfaces be selected?

A) Use each pinned component's supported native setup interface, called only by its own adapter with that component's separate admin credential. If the selected version lacks a needed operation, stop and record a feasibility blocker; do not introduce a new identity provider or broaden access (recommended; preserves ownership and version scope).

B) Introduce a common database-backed credential/account registry used by all components.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 5 — RustFS policy scope

What should the RustFS access boundary be for writer and test identities?

A) Use separate native access keys and the narrowest bucket/prefix policy the pinned RustFS version supports: writer limited to the intended warehouse paths; each test user limited to their allowed database paths. Keep bucket setup/admin credentials separate. If prefix policy is unavailable or unverified, stop short of claiming least privilege and return the smallest proposed change (recommended; matches approved FR-18/FR-23).

B) Give each workload user broad access to the entire `lake` bucket for simpler setup.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 6 — Network and credential mounts

What network and file-mount boundary should the provisioner use?

A) Use only the private Compose network and publish no provisioner port. Mount only the credential files required by each adapter; mount setup inputs read-only and write generated output to the host runtime credential directory with restricted permissions (recommended; follows approved NFR Design).

B) Publish a local provisioning API port and mount the full credentials directory into every component adapter.

X) Other (describe after `[Answer]:`)

[Answer]:A

### Question 7 — Hive and post-ETL authorization mechanism

How should Hive permission setup be represented in the infrastructure design?

A) Keep the approved standalone Hive Metastore/no-HiveServer2 architecture and map a Hive-owned authorization candidate only where exact behavior is supported. Treat writer permissions and post-ETL reader grants over RustFS as unverified integration gates; do not add HiveServer2 or another policy authority without review (recommended; preserves the approved architecture boundary).

B) Add HiveServer2 or another authorization service now to provide a permission interface.

X) Other (describe after `[Answer]:`)

[Answer]:A

## Feasibility Gates

- Confirm the pinned RustFS image supports distinct identities and the proposed prefix-scoped permissions.
- Confirm the pinned Dremio Community version's supported local-user setup interface and initial setup prerequisite.
- Confirm the selected Hive/Hadoop setup interface can express the required writer permissions and later reader grants without HiveServer2; do not treat Kerberos authentication as authorization.
- Confirm native admin mapping for components in US-ID-02, including how to represent Spark and the future JupyterHub boundary without inventing user stores.
- Confirm the provisioner can consume protected local files without secrets leaking through process arguments, environment dumps, logs, or image layers.

If a gate fails, record the observed limitation and smallest proposed adjustment for user review before changing an approved version, architecture, credential boundary, or privilege scope.

## Extension Compliance Summary

- **Security Baseline**: Disabled by user choice. Approved credential separation, local-only network, restricted files, and least privilege remain mandatory.
- **Property-Based Testing (Partial)**: Not applicable to this infrastructure design stage; no code or tests are introduced.
- **Resiliency Baseline**: Disabled by user choice. Safe retries, fail-fast dependencies, and persistent-state preservation remain required.

## Current Status

All seven answers are consistent with the approved functional/NFR designs. Unit 2 infrastructure artifacts are generated and ready for review. The existing Compose credential flow and PostgreSQL bootstrap role require explicit, non-destructive changes in Code Generation; no application configuration has changed in this design stage.
