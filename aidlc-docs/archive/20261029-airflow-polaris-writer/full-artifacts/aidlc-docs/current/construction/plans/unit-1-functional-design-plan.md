# Unit 1 Functional Design Plan — Airflow Writer Identity and Broker

## Unit context

Unit 1 owns the Airflow writer token broker, its per-run state and business rules, and the DAG lifecycle integration that creates and revokes run authorization. It defines the broker contract consumed by Unit 2's shared Spark token provider. It must preserve the existing two-Bundle contract and the user's main-only runtime verification boundary.

Approved application-level choices:

- A dedicated Airflow-boundary token broker owns/accesses the writer client secret.
- Each DAG run has a high-entropy renewal capability, bounded to the configured maximum run duration and revoked after the run.
- Spark calls the broker over verified HTTPS on a private Docker network.
- The initial writer access token is passed to Spark through a protected per-run handoff; the client secret is never exposed to Spark.
- The Spark provider and runtime are shared with Jupyter, with a distinct user-bound adapter and no writer identity fallback.

Current requirements and unit scope:

- One-hour access-token lifespan for the writer service account only.
- Long-running Spark refreshes the token without restarting the Spark application or Jupyter session.
- Polaris grants and RustFS policies remain unchanged; Polaris vends scoped storage credentials.
- Bundle definitions remain unchanged; only main/production receives runtime end-to-end verification.

## Existing component and canonical impact

The functional owner is the existing Airflow workload-execution component. The approved execution-plan inventory identifies `aidlc-docs/knowledge/opensource-lakehouse/functional-design/airflow-workload-execution.md` as a canonical component baseline to create at intent closure. The v2 application-design baseline also identifies Airflow as deferred; reconcile that baseline at closure as listed in the execution-plan inventory. This plan and subsequent functional artifacts remain active intent artifacts until approval and closure.

The current `opensource-lakehouse` canonical application design predates the Polaris writer flow and mentions Nessie/S3 behavior. Current approved requirements and this intent's Polaris application design supersede conflicting legacy descriptions.

Initial answers recorded Q1=A through Q5=A. Follow-ups selected the approved DAG-run capability scope and bounded renewal retry policy: one capability is reused across retries in the same DAG run; renewal allows three total requests, waiting 1 second and then 2 seconds, and stops retrying with 60 seconds or less remaining on the current token. Duplicate run creation uses the stable DAG/run idempotency key and a short-lived encrypted in-memory replay record, returning the same capability with a fresh JWT if the initial response was lost.

## Functional design plan

- [x] Read Unit 1 definition, dependency matrix, story map, approved requirements, and application design.
- [x] Identify the broker, DAG run, renewal capability, writer token, and cleanup lifecycle as core functional concepts.
- [x] Review canonical knowledge impact inventory and existing workload design baseline.
- [x] Resolve the follow-up in `unit-1-functional-design-clarification-questions.md`; analyze answers for ambiguity and contradictions.
- [x] Draft `business-logic-model.md`, `business-rules.md`, and `domain-entities.md` from answers received so far.
- [x] Finalize artifacts, validate FR-1 through FR-8 ownership/coverage, and prepare Unit 1 Functional Design approval before Unit 1 NFR Requirements.

## Clarification questions

Fill every `[Answer]:` tag. Enter the option letter if the recommendation is acceptable. These decisions define functional behavior; network implementation and capacity details remain for later design stages.

### Question 1 — DAG retry and capability lifecycle

If Airflow retries a task within the same DAG run after its Spark container or task failed, how should broker authorization work?

A) Give each attempt its own capability. Re-registering an attempt revokes the previous attempt's capability; the broker scopes it to the DAG ID, run ID, attempt number, and expiry (recommended).

B) Reuse one capability for every task attempt within the DAG run, and revoke it only after the whole DAG run ends.

X) Other; describe after the answer tag.

[Answer]:A

### Question 2 — Initial token and run registration flow

How should Airflow obtain the initial token while the broker owns the client secret?

A) Airflow asks the broker to create/register the run; the broker obtains the initial writer token and returns the initial token, expiry, and opaque run capability together. Airflow passes only those per-run values to the matching Spark container (recommended).

B) Airflow registers the run first, then makes a separate broker request for the initial token.

X) Other; describe after the answer tag.

[Answer]:A

### Question 3 — Token renewal trigger

When should the shared Spark provider request a replacement writer token?

A) Refresh when five minutes or less remain, then use the replacement token for subsequent Polaris requests; never wait until after expiry (recommended).

B) Refresh at a fixed fraction of the issued token lifetime, regardless of the remaining time.

C) Refresh only after Polaris rejects a request for an expired token.

X) Other; describe after the answer tag.

[Answer]:A

### Question 4 — Renewal registration state semantics

What should happen if the broker loses its in-memory run registration while Spark is still running?

A) Registration state is short-lived in-memory state; after broker restart, the current token remains usable until expiry, but renewal fails closed and Airflow must fail/clean up the Spark run (simplest; broker restart recovery is deferred).

B) Registration state must be durable across broker restarts so the same run capability can renew the writer token after a restart.

X) Other; describe after the answer tag.

[Answer]:A

### Question 5 — Temporary renewal failure

If Keycloak or the broker temporarily fails during a refresh request, what should Spark do?

A) Retry a small bounded number of times with backoff while the current token remains valid; if no replacement arrives before the token becomes unusable, fail the operation with a sanitized authentication error (recommended).

B) Fail the Spark application on the first renewal failure.

X) Other; describe after the answer tag.

[Answer]:A

## Applicability review

- Business logic, domain model, business rules, data flow, integration, errors, and retry/cleanup scenarios apply and are covered by the questions and planned artifacts.
- Frontend/UI questions are not applicable: Unit 1 has no user interface.
- Business domain is platform workload identity lifecycle; user-approved principal separation is fixed and will not be reopened here.
