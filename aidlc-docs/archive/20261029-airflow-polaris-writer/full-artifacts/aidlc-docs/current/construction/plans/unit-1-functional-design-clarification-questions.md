# Unit 1 Functional Design — Follow-up Questions

The initial answers are recorded in `unit-1-functional-design-plan.md`. These follow-ups resolve one design conflict and one underspecified retry policy before functional artifacts are generated.

## Follow-up 1 — Renewal capability scope on Airflow retry

Application Design approved one capability scoped to a DAG run and revoked when that DAG run ends. Your Q1 answer instead gives each task attempt a capability and revokes the previous capability on retry. Which scope should the functional design use?

A) Preserve the approved DAG-run scope: retries for the same DAG run use the same registered capability, and Airflow revokes it when the DAG run ends (recommended; no Application Design change).

B) Amend Application Design to use attempt-scoped capabilities: each attempt receives a new capability and the prior attempt capability is revoked. I will update and present Application Design for approval before finalizing Unit 1 Functional Design.

X) Other; describe after the answer tag.

[Answer]:A

## Follow-up 2 — Exact renewal retry bound

The Q5 answer selected bounded retries but did not specify the maximum. Which retry policy should the Spark provider use if a renewal request fails while the current token is still valid?

A) At most three total requests (one initial request plus two retries), with waits of 1 second and then 2 seconds. Do not start another request if the current token has 60 seconds or less remaining; fail closed with a sanitized error if renewal still fails (recommended).

B) One request only; fail immediately on renewal failure.

X) Other; specify maximum requests and delays after the answer tag.

[Answer]:A

## Follow-up 3 — Lost run-registration response

The chosen flow has the broker create/register a DAG-run capability and return it with the initial JWT. Airflow must reuse that capability on task retries. If the broker creates the registration but Airflow loses the response before it can save the capability, how should a repeated create request recover?

A) Use an Airflow idempotency key for `(dag_id, run_id)` and keep a short-lived encrypted in-memory replay record for the issued capability. A duplicate create request returns the same capability with a fresh initial JWT; the replay record is removed on run revocation/expiry (recommended; broker restart still loses in-memory state as already approved).

B) Reject duplicate creation. Airflow fails the run and cleans up; an operator must start a new DAG run.

X) Other; describe after the answer tag.

[Answer]:A
