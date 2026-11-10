# Unit 1 NFR Design Plan — Spark Writer Runtime

## Approved Baseline

Unit 1 is the existing local Spark standalone service (`tabulario/spark-iceberg:3.5.5_1.8.1`). It runs a Spark master, worker, and history server in one service. The approved NFRs require a valid writer TGT before readiness, a 15-minute renewal margin, retries at least once per minute, automatic recovery, protected runtime credentials/cache, sanitized health/logs, and a Spark-service boundary that blocks new work while allowing current work to finish. Do not add an external helper/service, package, principal, or production capacity target without an approved change.

## Design Checklist

- [x] Read the approved Unit 1 Functional Design, NFR Requirements, and technology decisions.
- [x] Define the credential lifecycle, renewal/reacquisition retry coordination, readiness state, and recovery state transitions.
- [x] Design Spark-service admission enforcement for invalid credentials and inspect the pinned image for its worker decommission command; runtime behavior remains for Build and Test.
- [x] Define private ticket-cache creation, credential mount protections, ownership/modes, and safe process interaction.
- [x] Define Docker health and sanitized log behavior, including startup and recovery timing.
- [x] Assess resilience, scalability, performance, security, and logical components against the approved local PoC scope.
- [x] Generate `aidlc-docs/current/construction/unit-1/nfr-design/nfr-design-patterns.md` and `logical-components.md`.
- [x] Present the NFR Design for explicit review and approval before Unit 1 Infrastructure Design.

## NFR Design Questions

Please fill each `[Answer]:` tag. The options are constrained by the approved NFR requirements; use X if none fits.

### Question 1 — Admission control when the TGT is invalid

The Spark worker must stop receiving new task assignments without deliberately terminating tasks already running. Which design constraint should govern the admission mechanism?

A) Use the pinned Spark version's graceful worker decommission mechanism if it is present and supports this behavior. If exact-image verification shows it is absent or cannot preserve active work, pause design and return with the concrete gap for a decision; do not silently upgrade or add dependencies.

B) Permit upgrading the Spark image to a version that provides a supported graceful worker decommission mechanism, if the pinned image lacks one; keep the no-new-assignments and active-work-drain requirements.

X) Other (describe the acceptable behavior and tradeoff after `[Answer]:`).

[Answer]:A

### Question 2 — Renewal and recovery process pattern

How should the Bash service coordinate the 15-minute renewal margin, one-minute retries, and recovery after a failed renewal?

A) Use one lifecycle supervisor loop with explicit `STARTING`, `READY`, `DRAINING/UNAVAILABLE`, and `RECOVERING` states. It performs a single serialized attempt at a time, schedules attempts no more than one minute apart, and gates readiness/admission around ticket validity.

B) Keep ticket renewal in a separate background loop and readiness/admission in a health monitor, with a shared state file between them.

X) Other (describe the process pattern after `[Answer]:`).

[Answer]:A

### Question 3 — Resilience and recovery behavior

What should the service do if Kerberos commands fail repeatedly or the cache becomes unreadable?

A) Keep retrying automatically at the approved cadence with bounded command timeouts and sanitized error categories. Remain unavailable for new work until a fresh TGT validates; do not terminate existing work merely due to the failure.

B) Retry automatically, but restart the Spark worker after a configured number of failed attempts to recover local process state.

X) Other (describe retry limits and recovery after `[Answer]:`).

[Answer]:A

### Question 4 — Security pattern for runtime cache and credentials

Which implementation pattern should the design require for the service ticket cache and mounted secrets?

A) Create the cache directory at service startup with owner-only access, set a service-private `KRB5CCNAME`, validate using that cache explicitly, keep keytab/RustFS secret mounts read-only, and avoid logging command output that could contain credential material.

B) Use the default Kerberos cache location and rely on container filesystem isolation; retain read-only mounts and sanitized logs.

X) Other (describe the protection pattern after `[Answer]:`).

[Answer]:A

### Question 5 — Scalability and performance scope

What should the NFR design assume about performance and scale for this unit?

A) Retain the existing single local Spark service and resource settings. Add only bounded Kerberos command timeouts and lightweight readiness checks; make no throughput, latency, or scale claims.

B) Add a concrete local workload target (describe concurrent jobs, task count, or readiness/recovery latency after `[Answer]:`).

X) Other (describe the target after `[Answer]:`).

[Answer]:A

### Question 6 — Logical components and operator visibility

Which logical decomposition should the design use?

A) Keep lifecycle supervision, TGT validation, admission state, and sanitized diagnostics inside the existing Spark service. Docker health reports readiness, while Spark worker admission control enforces it; no external monitor or queue is introduced.

B) Add a small separate readiness/admission sidecar in the Compose network so it can coordinate Spark health independently.

X) Other (describe the components and boundaries after `[Answer]:`).

[Answer]:A

## Evidence and Version Constraint

The project pins Spark 3.5.5. Read-only inspection of the running pinned image confirmed Spark 3.5.5 and `/opt/spark/sbin/decommission-worker.sh`; its script issues the Spark worker decommission action. Apache Spark's standalone documentation describes this command as gracefully draining a worker. This supports the selected design, but Build and Test must still verify runtime behavior: new tasks stop being assigned, in-flight tasks are not deliberately terminated, and the worker can rejoin after credential recovery. If that behavior does not hold, do not claim SWR-NFR-02 passes and return for a design decision. [Spark standalone documentation](https://spark.apache.org/docs/latest/spark-standalone.html)

## Approval Gate

Answers A/A/A/A/A/A are clear and consistent with approved requirements. NFR design artifacts are generated and await explicit approval before proceeding to Unit 1 Infrastructure Design.

**Status**: Design complete; awaiting explicit approval.
