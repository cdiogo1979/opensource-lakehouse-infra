# Unit 1 Functional Design Plan — Spark Writer Runtime

## Unit Context

Unit 1 owns the existing Spark service's writer credential lifecycle and the reviewed execution contract for the later Airflow driver. The target Compose Spark service currently hosts the master, worker, and history server in one container; `infra/spark/entrypoint.sh` starts the master and worker, and the worker startup URL is `spark://spark-iceberg:7077`. The approved design selects writer TGT acquisition and renewal inside this existing Spark service, using its private runtime cache. Unit 2 owns the per-run driver's separate cache and credential lifecycle.

The approved requirement is to use the existing `write-service-account@LAKEHOUSE.LOCAL` principal and matching RustFS credentials without rotation. Hive access is Kerberos-authenticated; RustFS access uses file-backed S3 credentials. Preserve existing catalog/data and do not infer per-author authorization from this shared service identity.

Canonical ownership remains the existing `aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/lakehouse-workload-and-access.md`, as listed in the approved execution-plan inventory. This is an active intent artifact; do not create or update canonical knowledge during this design stage.

## Functional Design Checklist

- [x] Read the approved Unit 1 definition, story assignment, dependencies, requirements, and Application Design.
- [x] Check the existing canonical lakehouse application/workload designs and execution-plan knowledge inventory.
- [x] Resolve the behavior questions below and check answers for ambiguity/contradiction. Answers A/A/A are explicit and consistent.
- [x] Define the writer credential lifecycle and Spark service availability rules.
- [x] Define business rules for ticket state, renewal failure, RustFS credential use, and workload identity scope.
- [x] Define functional entities/states and Spark-to-Hive/RustFS data flow.
- [x] Generate `aidlc-docs/current/construction/unit-1/functional-design/business-logic-model.md`.
- [x] Generate `aidlc-docs/current/construction/unit-1/functional-design/business-rules.md`.
- [x] Generate `aidlc-docs/current/construction/unit-1/functional-design/domain-entities.md`.
- [x] Validate against US-03, FR-4/FR-5, NFR-1/NFR-3, and the Unit 1 exit contract.
- [x] Present the functional design artifacts for explicit review and approval.

## Functional Scope

- Establish the worker-side writer identity before the Spark service accepts remote ETL work.
- Keep the Kerberos ticket cache private to the Spark service runtime and usable by the Spark processes that need Hive access.
- Maintain usable writer credentials for remote executors through the service's lifetime.
- Keep RustFS authentication sourced from the existing writer credential files, not the Kerberos ticket.
- Expose a stable, verified Spark master submission contract to Unit 2; exact DNS advertisement and networking are verified in Infrastructure Design.
- Report credential lifecycle failures without revealing keytab or secret values.

## Design Questions

Please fill each `[Answer]:` tag in this document. If none of the options fit, choose X and describe the desired behavior.

### Question 1 — Initial credential readiness

How should the Spark service treat writer ticket initialization when the existing keytab is missing, unreadable, or cannot obtain a valid TGT?

A) Fail closed: do not report the Spark worker as ready for ETL until a valid writer TGT is acquired; surface a clear non-secret failure.

B) Allow Spark to start, but keep the worker unavailable for new ETL jobs until the credential lifecycle recovers and readiness is restored.

X) Other (describe after `[Answer]:`).

[Answer]:A

### Question 2 — Renewal failure during service operation

If the current ticket cannot be renewed before expiry, what functional response should the writer lifecycle use?

A) Attempt to obtain a fresh TGT from the same keytab; if no valid TGT can be restored, mark the service unavailable for new ETL work and report the failure. Do not silently continue using an expired ticket.

B) Retry renewal/reacquisition while continuing to accept new work until the current ticket expires, then stop accepting work and report unavailable.

X) Other (describe after `[Answer]:`).

[Answer]:A

### Question 3 — Effect on running workloads

If credentials become unavailable while a Spark workload is already running, how should the service handle that workload?

A) Do not deliberately terminate it; allow Spark/Hive/RustFS operations to succeed or fail according to their actual authentication result, while blocking new ETL work until credentials recover.

B) Fail active ETL workloads as soon as the credential lifecycle declares the service unavailable, then block new work until recovery.

X) Other (describe after `[Answer]:`).

[Answer]:A

## Explicitly Deferred to Later Design

- NFR Design will set cache permissions, renewal lead time/interval, retry limits/backoff, and health signaling details.
- Infrastructure Design will verify mount ownership/modes, service dependency ordering, actual master-advertised endpoint, Compose DNS, and executor callbacks.
- Functional Design for Unit 2 will define the per-run driver's separate ticket-cache lifecycle and submission cleanup.
- No UI/front-end artifacts apply to this unit.

## Approval Gate

After answers are reviewed and any ambiguity resolved, generate the three Functional Design artifacts and request explicit approval before proceeding to Unit 1 NFR Requirements.

**Status**: Answers A/A/A are recorded. Functional Design artifacts are generated and await explicit review and approval.
