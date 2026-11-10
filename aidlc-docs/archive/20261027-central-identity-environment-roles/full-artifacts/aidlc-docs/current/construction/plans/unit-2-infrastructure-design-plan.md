# Unit 2 Infrastructure Design Plan — RustFS Role Policies and Reconciliation

## Unit and Approved Baseline

Unit 2 extends the existing operator-triggered identity-provisioner to reconcile FreeIPA role membership with exact RustFS IAM groups and policies for `lake`, `lake-dev`, and `lake-uat`. It preserves production objects, existing `admin` mapping, the writer S3 credential, and legacy `user_a`/`user_b` until verified cutover. Only absent `lake-dev` and `lake-uat` may be created. RustFS remains on the pinned `rustfs/rustfs:1.0.0-glibc` image and internal Compose endpoint.

The approved design requires fail-closed preflight, a single active run, idempotent changes, partial-failure reporting, protected pre-change IAM state, sanitized status, deterministic dependencies, exact policy/binding readback, and non-root positive/negative S3 probes. The active MIT KDC remains authoritative; FreeIPA remains an isolated validation instance. Infrastructure decisions must provide the reconciler a controlled read-only route to that validation instance without joining it to the workload/KDC network or changing identity authority.

Current implementation context: `identity-provisioner` is a one-shot Compose profile on `iceberg_net`, mounts `.runtime/identity-provisioning` at `/run/identity-status`, and currently combines Kerberos, PostgreSQL, and RustFS provisioning. Its RustFS client uses the pinned RustFS internal service endpoint, Python standard-library HTTP with SigV4 signing, and a 15-second request timeout. The provisioner base image is digest-pinned, but some OS and Python package inputs are not fully locked. These are findings to resolve, not approved final implementation choices.

## Infrastructure Design Checklist

- [x] Review approved Unit 2 functional and NFR design artifacts and identify implementation-level decisions left open.
- [x] Inspect current Compose networks, identity-provisioner invocation, secret mounts, runtime status mount, provisioner image, and RustFS client stack without changing runtime state.
- [x] Select an explicit operator invocation path that does not accidentally rerun unrelated identity/Kerberos/PostgreSQL provisioning: A.
- [x] Select the reconciler's controlled network path to the isolated FreeIPA validation instance and RustFS; preserve MIT KDC authority and avoid attaching general workload clients to FreeIPA: A.
- [x] Specify a dedicated read-only FreeIPA query principal, TLS CA trust, credential delivery, and mount permissions; keep it separate from FreeIPA admin and membership mutation credentials: A.
- [x] Select the single-run lock and sanitized status implementation on the existing single-host Compose setup, including operator-reviewed stale-state handling: A.
- [x] Specify sensitive IAM snapshot capture, storage, restrictive permissions, retention/cleanup ownership, and isolated restore verification: A.
- [x] Specify deterministic OS/Python dependency resolution for the existing provisioner image without adding a service or unreviewed dependency stack: A.
- [x] Specify internal RustFS endpoint use, finite timeout/retry classification, and how supported admin API responses are tested against the pinned RustFS image: A.
- [x] Confirm localhost-only/no-new-host-port boundaries and secret-safe logs/status: A.
- [x] Generate `construction/unit-2/infrastructure-design/infrastructure-design.md` and `deployment-architecture.md`.

Answers recorded as A/A/A/A/A/A/A/A using the plan's recommended options after the user approved continuation on 2026-10-27. A narrow `python3-ldap` package is proposed in the existing provisioner image because the approved live read-only LDAP contract cannot be implemented with its current Python dependencies; its package version will be fixed from the selected Debian snapshot and is included for explicit review with these infrastructure artifacts.

## Infrastructure Design Questions

Complete each `[Answer]:` field. Recommended options preserve the approved PoC boundaries; choose `X` and describe the desired behavior if none fits.

### Question 1 — Operator invocation and process scope

How should an operator invoke RustFS reconciliation through the existing identity-provisioner?

A) Add a distinct explicit reconciliation command/profile using the existing provisioner image and codebase. Keep it separate from Kerberos keytab and PostgreSQL role provisioning, and run it only on operator request. **(Recommended)**

B) Extend the existing aggregate provisioning command and run RustFS reconciliation whenever any identity-provisioning command is invoked.

X) Other (describe the invocation and which existing provisioning actions it may trigger).

[Answer]:A

### Question 2 — Network access to isolated FreeIPA

How should the reconciler read FreeIPA membership while FreeIPA remains isolated from workload clients and the MIT KDC remains authoritative?

A) Permit only the explicitly invoked reconciler container to join both the existing RustFS/Compose network and the isolated FreeIPA validation network. Do not add FreeIPA to the general workload network, publish LDAP/Kerberos/DNS ports, or change KDC aliases. Validate routing and DNS from that single client. **(Recommended)**

B) Keep networks fully separate and pass a reviewed, sanitized directory-membership snapshot to the reconciler for each run; no live LDAP connection is made by Unit 2.

X) Other (describe the network and identity-authority boundary).

[Answer]:A

### Question 3 — Read-only directory identity and TLS

How should LDAP credentials and server trust be supplied?

A) Create a dedicated FreeIPA read-only query principal for the approved users/groups; deliver its password through a protected read-only secret file and mount only the public FreeIPA CA certificate read-only. Require certificate and hostname validation. Keep this identity separate from FreeIPA `admin` and the membership mutator. **(Recommended)**

B) Use the existing FreeIPA admin identity for LDAP reads, with the password mounted read-only.

X) Other (describe bind identity, credential delivery, and TLS trust).

[Answer]:A

### Question 4 — Lock and status storage

How should a single active run and its status be represented?

A) Use the existing ignored host runtime directory `.runtime/identity-provisioning`, mounted into the one-shot container with restrictive permissions. Use an OS-managed advisory lock whose ownership releases when the process exits; retain a sanitized status record, and require operator inspection before acting on stale status. **(Recommended)**

B) Add a separate named Docker volume for coordination and status, with an operator command to inspect and clear stale state.

X) Other (describe locking, persistence, access, and stale-run handling).

[Answer]:A

### Question 5 — IAM snapshot storage and recovery

Where should pre-change RustFS IAM exports be stored and how should restore be controlled?

A) Store exports under a dedicated ignored `.runtime/identity-provisioning` subdirectory with owner-only permissions; never print or commit contents. Document operator-controlled cleanup and test restore only against a separate isolated RustFS instance. Never automatically apply an export to live state. **(Recommended)**

B) Store exports in another protected location specified in `X`, with separate backup ownership and lifecycle.

X) Other (describe storage, permissions, retention, and restore control).

[Answer]:A

### Question 6 — Reproducible provisioner dependencies

How should the current digest-pinned Debian provisioner base and package set be made deterministic?

A) Keep the approved base-image digest and use an immutable Debian snapshot/repository timestamp with exact OS package versions; pin the Python dependency set and record its lock/verification method. Do not add a service. **(Recommended)**

B) Replace the package source/runtime with another reproducible, pinned mechanism described in `X`.

X) Other (describe the base, OS repository, Python dependency, and update approach).

[Answer]:A

### Question 7 — RustFS endpoint, timeouts, and retry behavior

How should the reconciler call RustFS and classify transient failures?

A) Use only `http://object-store:9000` on the internal Compose network and the existing SigV4 client stack. Keep finite per-call timeouts, classify responses with an allowlist verified against the pinned image, and do not blindly retry mutations; re-read state before any safe retry. **(Recommended)**

B) Add a separate TLS proxy or admin endpoint for reconciliation and define its lifecycle in `X`.

X) Other (describe endpoint, transport, timeout, and retry rules).

[Answer]:A

### Question 8 — Host exposure and secret/log boundaries

What host exposure and runtime diagnostic boundary should Unit 2 use?

A) Publish no new host port. Keep RustFS administration and LDAP traffic internal; mount only required read-only secret/trust files, and emit the approved sanitized status fields without raw API bodies or principal keys. **(Recommended)**

B) Publish a localhost-only reconciliation/admin endpoint for operator use and describe authentication and logging in `X`.

X) Other (describe exposure, secret mounts, and diagnostics).

[Answer]:A

## Design Constraints

- Do not start or modify RustFS, FreeIPA, MIT KDC, Compose services, role membership, credentials, buckets, policies, bindings, or objects while answering or drafting this design.
- FreeIPA remains an isolated validation identity source; do not cut over authority, change `kdc` aliases, or attach general workload clients to FreeIPA.
- Preserve the approved role policy matrix and all Unit 2 functional/NFR constraints.
- Do not add an always-on controller, scheduler, service, public/host-published admin API, or dependency stack without explicit review.
- Runtime Build and Test must use isolated state and the pinned RustFS digest. No live policy application is part of Infrastructure Design.

## Approval Gate

Answers A/A/A/A/A/A/A/A are recorded as the recommended defaults after the user requested continuation. Review `construction/unit-2/infrastructure-design/` artifacts, including the narrowly scoped pinned LDAP client package, before Unit 2 Code Generation Planning.
