# Unit 2 NFR Requirements Plan — StarRocks Runtime

## Unit Context

- **Unit:** Unit 2 — StarRocks Runtime.
- **Approved Functional Design:** `aidlc-docs/current/construction/unit-2-starrocks-runtime/functional-design/`.
- **Scope:** Local single-FE/single-BE StarRocks runtime, protected Unit 1 credential consumption, TGT refresh behavior, FE/BE state persistence, loopback endpoints, and operator readiness/diagnostics.
- **Out of scope:** Production HA, cloud deployment, end-user Kerberos impersonation, catalog SQL setup, user grants, and Airflow/Jenkins.
- **Fixed technology decisions:** Docker Compose; StarRocks OSS; one FE plus one BE; pin a reviewed compatible stable release and digest rather than using `latest`; retain the existing lakehouse services and named volumes.

## NFR Assessment Tasks

- [x] **Step 1 — Analyze Functional Design:** Review the approved business logic, rules, domain entities, and user-selected runtime recovery behavior.
- [x] **Step 2 — Establish fixed constraints:** Carry forward local-only exposure, credential redaction, persistence, single-node scope, and approved technology choices.
- [x] **Step 3 — Identify remaining NFR decisions:** Prepare questions for capacity, startup expectation, recovery objective, local resource budget, and diagnostic retention.
- [x] **Step 4 — Resolve questions:** All five answers are A and consistent with the approved PoC boundary and Functional Design.
- [x] **Step 5 — Generate NFR artifacts:** Created `nfr-requirements.md` and `tech-stack-decisions.md` under `aidlc-docs/current/construction/unit-2-starrocks-runtime/nfr-requirements/`.
- [x] **Step 6 — Validate and present:** Traced NFRs to approved FRs and Functional Design. Artifacts are presented for explicit approval before NFR Design.
- [x] **Step 7 — Record approval:** User approved NFR Requirements on 2026-10-24; advanced to Unit 2 NFR Design.

## Questions

Fill each `[Answer]:` line with an option letter. Choose the last option, `Other`, and describe your choice if none fits.

### Question 1 — Expected PoC workload and capacity

What workload should the runtime resource requirements target?

A) Existing sample databases and occasional interactive SQL use; document a tested local baseline without a concurrency or throughput SLA.

B) Define target data size and concurrent SQL sessions; provide the expected values after `[Answer]:`.

C) Target sustained multi-user analytical workloads beyond the existing sample data; describe the workload after `[Answer]:`.

D) Other (please describe after `[Answer]:` below)

[Answer]: A

### Question 2 — Startup and readiness expectation

What startup-time requirement should apply to this local PoC?

A) No hard time objective; document observed startup time and report readiness only after both FE and BE are healthy.

B) Require readiness within a specified time after `docker compose up`; provide the target and conditions after `[Answer]:`.

C) Other (please describe after `[Answer]:` below)

[Answer]: A

### Question 3 — Recovery objective

What recovery expectation should apply after a process or node failure?

A) Best effort: allow configured Compose process recovery, preserve both volumes, and require operator action for persistent failures; no fixed recovery-time objective.

B) Require a recovery-time objective; provide the target and acceptable retry behavior after `[Answer]:`.

C) Do not automatically restart failed StarRocks processes; require operator restart while preserving volumes.

D) Other (please describe after `[Answer]:` below)

[Answer]: A

### Question 4 — Host resource budget

How should the local CPU, memory, and storage requirements be constrained?

A) No fixed host budget; document measured minimum and recommended resources for the pinned, verified FE/BE combination.

B) Enforce a fixed Compose CPU/memory budget; provide host limits after `[Answer]:`.

C) Other (please describe after `[Answer]:` below)

[Answer]: A

### Question 5 — Runtime diagnostics and retention

How should runtime logs and diagnostics be retained for this PoC?

A) Use container stdout/stderr and Docker Compose log access; no persistent log store or monitoring service, with credential redaction required.

B) Write rotated local logs with a defined size/retention limit; provide the limit after `[Answer]:`.

C) Add a local monitoring or log-collection component; describe the required signals after `[Answer]:`.

D) Other (please describe after `[Answer]:` below)

[Answer]: A

## Fixed Security and Compatibility Constraints

## Answer Review

- **Q1 A:** Size for existing sample databases and occasional interactive SQL use; no concurrency/throughput SLA.
- **Q2 A:** No startup-time objective; document observed time and report readiness only when FE/BE are healthy.
- **Q3 A:** Best-effort Compose process recovery, preserve volumes, and require operator action for persistent failures; no RTO.
- **Q4 A:** No fixed host budget; document measured minimum and recommended resources for the verified pinned combination.
- **Q5 A:** Use Compose stdout/stderr and Docker logs; no persistent log store/monitoring, and redact credentials.

- SQL and FE UI host ports remain bound to loopback only.
- Keytabs and RustFS secret files remain outside tracked configuration and are consumed read-only; secret values and ticket contents are never logged.
- TGT refresh retries while the current ticket remains valid; a refresh failure is reported as credential degradation without taking down the runtime. Exact refresh scheduling is selected in NFR/Infrastructure Design against the pinned release and ticket lifetime.
- The image is pinned to a reviewed compatible StarRocks OSS version/digest; Hive Metastore 3.1.3, Iceberg table features, Kerberos, and RustFS compatibility must be verified.
- Security Baseline and Resiliency Baseline extensions are disabled. Explicit project security and recovery requirements remain binding. Property-Based Testing is partial and applies only if implementation later introduces qualifying pure functions or serialization round-trips.
