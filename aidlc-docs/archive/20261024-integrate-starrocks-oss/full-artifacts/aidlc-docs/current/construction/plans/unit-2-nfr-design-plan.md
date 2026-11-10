# Unit 2 NFR Design Plan — StarRocks Runtime

## Unit Context

- **Unit:** Unit 2 — StarRocks Runtime.
- **Inputs:** Approved Functional Design and NFR Requirements under `aidlc-docs/current/construction/unit-2-starrocks-runtime/`.
- **Design focus:** FE/BE process recovery, fixed-topology capacity, baseline performance, protected Kerberos ticket handling, paired-state startup validation, and logical runtime components.
- **Fixed scope:** One FE and one BE in Docker Compose, persistent named volumes, loopback-only host endpoints, no production HA, no added monitoring stack, no user Kerberos impersonation, and no catalog/SQL bootstrap.

## Documentation Finding — Kerberos TGT Lifecycle

The official [StarRocks Hive Catalog documentation](https://docs.starrocks.io/docs/data_source/catalog/hive_catalog/) says to run `kinit -kt keytab_path principal` on each FE and BE and use cron to refresh tickets periodically. It also specifies the `java.security.krb5.conf` setting for each FE/BE configuration. This constrains the design to refresh tickets on both nodes; the container process arrangement and cache handling still need a decision.

## NFR Design Tasks

- [x] **Step 1 — Analyze NFR Requirements:** Review availability/recovery, fixed PoC capacity, security, ticket lifecycle, persistence, compatibility, and operator diagnostics.
- [x] **Step 2 — Identify applicable design patterns:** Evaluate resilience, scalability, performance, security, and logical runtime components. Production HA, horizontal scaling, and persistent monitoring are not applicable to the approved scope.
- [x] **Step 3 — Identify implementation choices needing clarification:** Prepare questions on process restart behavior, vertical sizing, tuning baseline, TGT cache protection/refresh scheduling, and paired-state preflight.
- [x] **Step 4 — Resolve questions:** All six answers are A and consistent with the approved NFR/Functional Design; the in-container refresh task follows the cited StarRocks guidance.
- [x] **Step 5 — Generate NFR design artifacts:** Created `nfr-design-patterns.md` and `logical-components.md` under `aidlc-docs/current/construction/unit-2-starrocks-runtime/nfr-design/`.
- [x] **Step 6 — Validate and present:** Traced the patterns and components to approved requirements and StarRocks documentation. Artifacts are presented for explicit approval before Infrastructure Design.
- [x] **Step 7 — Record approval:** User approved with “approve and continue”; approval recorded in `audit.md` and `aidlc-state.md` advanced to Unit 2 Infrastructure Design.

## Questions

Fill each `[Answer]:` line with an option letter. Choose the last option, `Other`, and describe your choice if none fits.

### Question 1 — Process recovery pattern

Which Compose process recovery pattern should the FE/BE services use?

A) Restart a container when its process exits unless an operator stopped it; if a process stays alive but health checks fail, report not ready and require operator action. Preserve both volumes.

B) Do not configure automatic process restart; require the operator to restart a failed FE or BE. Preserve both volumes.

C) Use a bounded automatic restart policy, then stop retrying and require operator action; specify the retry limit after `[Answer]:`.

D) Other (please describe after `[Answer]:` below)

[Answer]: A

### Question 2 — Scaling pattern

How should capacity changes be handled while retaining the approved one-FE/one-BE topology?

A) Keep topology and resource settings fixed in Compose; an operator edits Compose configuration if the documented workload outgrows the baseline.

B) Keep one FE and one BE, but make CPU/memory settings operator-configurable through Compose environment/configuration; no automatic scaling.

C) Add horizontal scaling or automatic scaling beyond one FE/BE.

D) Other (please describe after `[Answer]:` below)

[Answer]: A

### Question 3 — Performance pattern

With no hard latency or throughput target, what performance approach should the design use?

A) Start from the selected release's defaults, measure startup and local resource use, and only tune settings if compatibility or observed operation requires it.

B) Add StarRocks-specific memory/cache tuning for the current sample workload before measuring; describe the tuning goal after `[Answer]:`.

C) Other (please describe after `[Answer]:` below)

[Answer]: A

### Question 4 — TGT cache protection

Where should the TGT cache produced by periodic `kinit` tasks reside on each FE/BE node?

A) In a per-container memory-backed temporary filesystem with restrictive file permissions; do not persist the cache in the FE/BE data volumes.

B) In a per-container temporary writable filesystem with restrictive permissions; it is lost when the container is recreated.

C) In a dedicated persistent named volume per node so the cache survives container recreation.

D) Other (please describe after `[Answer]:` below)

[Answer]: A

### Question 5 — Ticket refresh component pattern

Official StarRocks guidance calls for periodic `kinit -kt` on every FE and BE. Which runtime arrangement should implement this?

A) Run a periodic refresh task within each FE and BE container, using its read-only keytab and local ticket cache; keep the task independently observable and avoid printing ticket details.

B) Run a dedicated Compose helper per node that performs `kinit` and shares only that node's protected ephemeral ticket cache with its FE/BE process.

C) Do not run an automatic refresh task; rely on an operator to refresh tickets manually.

D) Other (please describe after `[Answer]:` below)

[Answer]: A

### Question 6 — Paired-volume startup validation

How should the runtime enforce the approved rule that both empty FE/BE locations may initialize together, but one-sided empty or invalid state must fail safely?

A) Use one startup preflight/init coordinator that checks both locations before either node starts and gates FE/BE startup on the pair result.

B) Put the same state check in both FE and BE entrypoints; each node decides independently whether to initialize itself.

C) Leave validation to the StarRocks processes and document manual recovery if startup produces inconsistent state.

D) Other (please describe after `[Answer]:` below)

[Answer]: A

## Answer Review

- **Q1 A:** Restart containers after process exit unless explicitly stopped; health failures report not ready and require operator action; preserve volumes.
- **Q2 A:** Keep FE/BE topology and resource settings fixed in Compose; operator edits Compose if the documented workload outgrows the baseline.
- **Q3 A:** Use release defaults and measure; tune only for compatibility or observed operational need.
- **Q4 A:** Keep each TGT cache on a per-container memory-backed temporary filesystem with restrictive permissions; do not persist it in node data volumes.
- **Q5 A:** Run the periodic `kinit` refresh task inside each FE and BE container, independently observable and secret-redacted.
- **Q6 A:** Use a single preflight/init coordinator to validate both volume states and gate FE/BE startup.

## Applicability Notes

- **Resilience:** Applicable as best-effort container-process recovery and safe fail-closed state validation. HA, failover, and a recovery-time objective are out of scope.
- **Scalability:** Horizontal scaling is outside the approved single-node scope. Question 2 covers whether vertical resource settings are fixed or operator-configurable.
- **Performance:** No SLA is set. Question 3 covers defaults versus preemptive tuning; measured observations are documented later.
- **Security:** Keytab secrecy, read-only mounts, no ticket/secret logging, local-only endpoints, and a dedicated service identity are fixed. Question 4 resolves the transient TGT cache location; Question 5 resolves the refresher arrangement.
- **Logical components:** No queue, cache tier, monitoring service, or new orchestration framework is approved. Question 6 resolves the minimum paired-volume startup gate; ticket refresh follows the official StarRocks guidance linked above.
- Security and Resiliency Baseline extensions are disabled. The partial Property-Based Testing extension does not prescribe architecture patterns at this stage.
