# NFR Design Plan — Unit 5 JupyterHub and Per-User Spark

## Scope

Translate the approved Unit 5 NFR requirements into concrete resilience, capacity, performance, security, and component design patterns for the local JupyterHub deployment and isolated Spark sessions. Keep the approved JupyterHub 5.3.0 and Spark 3.5.5/Iceberg 1.8.1 baselines, support up to three concurrent user containers, and preserve the localhost-only DummyAuthenticator boundary.

This stage defines design patterns and logical responsibilities only. It does not modify Compose or image files, resolve dependency versions, start services, or run tests.

## NFR Category Assessment

| Category | Applicability | Design focus |
|---|---|---|
| Resilience | Applicable | Fail-fast session startup, per-session error isolation, manual recovery, and preservation of user volumes. |
| Scalability | Applicable within fixed scope | Three isolated sessions on one host; no horizontal scale-out; admission behavior under local resource limits needs confirmation. |
| Performance | Applicable without SLA | Keep per-session Spark local and deterministic; confirm whether baseline defaults suffice or explicit resource tuning is wanted. |
| Security | Applicable | Loopback-only Hub, DummyAuthenticator limitation, exact user mapping, Hub-only Docker socket, non-root user containers, read-only keytabs, private ticket caches, and matching RustFS identity injection. |
| Logical components | Applicable | Confirm whether the existing Hub, DockerSpawner, user containers, existing platform services, and local evidence are sufficient, or any health/monitoring component is required. |

## Design Checklist

- [x] Resolve the resilience, scaling/admission, Spark tuning, container security, and logical component questions in `unit-5-nfr-design-questions.md` (A/A/A/A/A).
- [x] Define failure classification and manual recovery patterns without automated authorization retries or shared-identity fallback.
- [x] Define resource/admission and performance patterns for up to three user sessions on one host.
- [x] Define credential and container trust boundaries for the Hub, DockerSpawner, and single-user containers.
- [x] Map logical component responsibilities and interfaces without adding components unless approved.
- [x] Create `construction/unit-5-jupyter/nfr-design/nfr-design-patterns.md` and `logical-components.md`.
- [x] Update workflow state and audit trail; present the NFR Design for explicit review before Infrastructure Design.

## Questions and Approval

Answers were validated as A/A/A/A/A: fail and recover sessions manually; let local resource exhaustion affect only the requested session without queuing or evicting; retain Spark defaults without tuning; run single-user containers as non-root without privileged mode or Docker socket, with the socket mounted only in Hub; and add no health/monitoring or other platform components. The NFR Design artifacts are ready for user review and explicit approval.
