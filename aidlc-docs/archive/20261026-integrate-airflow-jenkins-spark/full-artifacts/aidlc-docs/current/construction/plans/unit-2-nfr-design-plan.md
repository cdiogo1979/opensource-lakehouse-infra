# Unit 2 NFR Design Plan — Airflow Bundle Runner

## Approved Baseline

Unit 2 NFR Requirements were approved on 2026-10-26. Each Airflow DAG run creates one ephemeral Spark driver and one worker-only container, with no more than two runs active and further runs queued. Each pair uses the writer service identity with separate per-container Kerberos caches. Both containers must be ready within five minutes and removed within 60 seconds of the DAG reaching a terminal state. The per-run worker registers with the shared Spark Standalone master; executors may be scheduled on any registered worker. The long-lived Spark service remains available for notebooks and other clients.

The user selected a bounded drain for shared-worker teardown: decommission the run worker, wait for other applications' executors to leave within the same 60-second paired-cleanup budget, and stop/remove the worker on timeout. A timeout is reported as a sanitized event; the remaining executors may be interrupted and another run may retry or fail. Exclusive placement is not required.

## Design Checklist

- [x] Read approved Unit 2 Functional Design and NFR Requirements, and the Unit 1 worker runtime boundary.
- [x] Trace run-pair startup, readiness, credentials, shared-master registration, concurrency, and terminal cleanup constraints.
- [x] Resolve the effect of removing a shared worker that still hosts executors for another run; drain up to 60 seconds, then remove and report timeout.
- [x] Define paired lifecycle states, readiness polling/failure transitions, partial-start cleanup, and terminal cleanup sequencing.
- [x] Define concurrency admission and queue behavior for a maximum of two active runs.
- [x] Define private credential/cache handling and safe diagnostics for both containers.
- [x] Define resilience and failure behavior without introducing performance or capacity claims.
- [x] Generate `aidlc-docs/current/construction/unit-2/nfr-design/nfr-design-patterns.md` and `logical-components.md`.
- [x] Validate alignment with Unit 2 Functional Design, NFR Requirements, the Unit 1 worker interface, and Airflow Bundle/Docker lifecycle boundaries.
- [x] Present the NFR Design for explicit review and approval before Unit 2 Infrastructure Design.

## Design Constraints

- Preserve the approved limit of two concurrent runs, five-minute readiness deadline, five-second-or-faster readiness checks, and 60-second paired cleanup unless the user changes one of these requirements.
- Do not claim worker affinity or exclusive placement. Spark Standalone is allowed to schedule executors across registered workers.
- Do not remove shared or long-lived services, persistent catalogs, data, or volumes as part of a run's cleanup.
- Treat three-catalog Hive/Iceberg Spark/StarRocks/RustFS compatibility and authorization as later integrated Build and Test gates.
- Do not add services, packages, identities, performance targets, or capacity claims without an approved change.

## Approval Gate

The completed NFR Design requires explicit user approval before Unit 2 Infrastructure Design.

**Status**: Design complete; awaiting explicit approval.
