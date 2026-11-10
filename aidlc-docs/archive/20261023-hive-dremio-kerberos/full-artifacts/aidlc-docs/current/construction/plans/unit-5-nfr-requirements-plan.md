# NFR Requirements Plan — Unit 5 JupyterHub and Per-User Spark

## Scope

Assess non-functional requirements for the local JupyterHub deployment and isolated single-user Spark sessions defined in the approved Unit 5 Functional Design. Cover fixed PoC capacity, startup/query performance expectations, local recovery and work-volume preservation, security/evidence boundaries, and package/image compatibility. Preserve the design's localhost-only DummyAuthenticator scope, matching per-user credentials, persistent separate work volumes, and no shared writable notebooks.

This stage produces NFR requirements and technology decisions only. It does not change Compose, build images, create credentials, start/restart services, or run tests.

## Baseline and Constraints

- Existing local PoC and Compose deployment; no production availability or horizontal-scale target is approved.
- Three configured labels (`user_a`, `user_b`, `admin`); one isolated notebook container and local Spark process per active session.
- JupyterHub baseline from sibling `jupyter-platform/` is 5.3.0; its Spark single-user image uses the target PoC's current Spark 3.5.5 / Iceberg 1.8.1 image line.
- DummyAuthenticator is accepted only for local development, and Hub access is restricted to the local machine.
- User keytabs remain read-only and separate, ticket caches remain session-private, and each session receives only its matching RustFS identity.
- Work volumes persist independently per username; platform data and credentials must not be reset as a recovery action.
- Existing cross-engine authorization and RustFS enforcement feasibility findings remain separate runtime gates; this stage makes no pass claim.

## Assessment Checklist

- [x] Validate the expected concurrent-session capacity and performance target in `unit-5-nfr-requirements-questions.md` (A/A).
- [x] Define local failure recovery, workspace/data preservation, and any backup expectations (A).
- [x] Carry forward security, privacy, secret-handling, localhost exposure, and redacted-evidence requirements.
- [x] Set image and package compatibility/version-management constraints for the JupyterHub and Spark single-user environments (A).
- [x] Create `construction/unit-5-jupyter/nfr-requirements/nfr-requirements.md` and `tech-stack-decisions.md`.
- [x] Update workflow state and audit trail; present NFR requirements for explicit review before NFR Design.

## Questions and Approval

Answers were validated as A/A/A/A: support up to three concurrent sessions without a scaling target; no numeric startup/query SLA; operator-led session recovery preserving work volumes without automatic backup/restore; and preserve the existing JupyterHub/Spark image baselines while pinning compatible Python dependencies before implementation. The NFR requirements and technology decisions are ready for user review and explicit approval.
