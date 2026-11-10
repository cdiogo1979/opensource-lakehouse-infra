# Unit 1 NFR Requirements Clarification

## Question 1 — Enforcing the unavailable state

The approved Unit 1 Functional Design says that when no valid writer TGT is available, new ETL work must be blocked while active workloads are not deliberately terminated. Your answer to NFR Question 4 selected Docker health status plus sanitized logs. A Docker health status reports readiness to observers, but does not by itself stop Spark from accepting/queueing submissions or assigning new tasks.

Which admission boundary should enforce the unavailable state?

A) **Spark service boundary** — Unit 1 must make the Spark worker unavailable for new ETL tasks when credentials are invalid, while preserving already-running tasks. The concrete Spark mechanism will be designed later and verified before implementation.

B) **Airflow submission boundary** — Unit 1 exposes an unhealthy/readiness state; Unit 2's Airflow runner checks it and refuses new Airflow Spark submissions while unavailable. Other clients that submit directly to Spark are outside this gate.

X) Other (describe the intended admission boundary after `[Answer]:`).

[Answer]:A

## Status

Resolved: the Spark service boundary must make the worker unavailable for new ETL tasks when credentials are invalid while preserving already-running tasks. The concrete Spark mechanism will be designed and verified in NFR Design and Infrastructure Design.
