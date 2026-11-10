# Unit 2 NFR Requirements — Clarification

Your NFR Question 1 answer sets a maximum of two concurrent DAG runs and says each run should create one driver and one worker. The approved Unit 2 Functional Design creates one ephemeral driver per DAG run and submits it to the existing shared Spark worker service; it does not create per-run Spark worker containers. A dedicated worker per run changes service boundaries, resource use, credentials, registration, and cleanup behavior.

## Question 1 — Spark worker lifecycle per DAG run

Which topology do you intend for the two concurrent DAG runs?

A) Keep the approved topology: each DAG run creates one ephemeral driver; both drivers submit to the existing shared Spark worker service. No per-run worker container is created.

B) Change the topology: each DAG run creates one ephemeral driver and one dedicated ephemeral Spark worker, both removed after the run. Keep the existing long-lived Spark worker for notebooks and other clients. This requires revising the Functional Design and the Unit 1/Unit 2 infrastructure/code boundaries before NFR requirements can proceed.

C) Other; describe which driver/worker containers exist per run, which workers process Airflow tasks, and what happens to the existing Spark worker service.

**[Answer]:**B

## Already-resolved answers

- Maximum concurrency: two active DAG runs; additional runs wait in the Airflow queue.
- Driver readiness: five minutes from container start, polling at least every five seconds; fail and clean up on timeout.
- Driver cleanup: graceful stop immediately and ensure removal within 60 seconds; report cleanup failure if the limit is exceeded.
- Authorization verification: verify writer create/write, reader read, reader write denial, storage-prefix boundaries, and StarRocks query-only behavior for all three catalogs using disposable test data.
- Performance/capacity: no numeric throughput, latency, or capacity claim; retain existing service resources except for the selected two-run concurrency bound.

## Question 2 — Worker assignment and isolation

The selected design adds one dedicated Spark worker container for each DAG run and registers it with the existing Spark master. Spark Standalone schedules application resources across workers; simply adding a worker does not guarantee the run's application uses only that worker. The existing long-lived worker and the other run's worker may also receive its executors. [Spark Standalone scheduling documentation](https://spark.apache.org/docs/3.5.6/spark-standalone.html)

Which behavior is required?

A) Create one worker per run as requested, but allow Spark Standalone to schedule that run's executors across any available workers. No exclusive worker assignment is required.

B) Each run must execute only on its own worker. This requires a design for hard placement/isolation (for example, an isolated master/cluster per run or a verified supported scheduling mechanism). Revise the topology accordingly; do not claim pairing based only on registering a worker with the shared master.

C) Other; describe the required isolation and whether each run may share the existing master or other workers.

**[Answer]:**A

## Gate

**[Resolution]:** The design creates one ephemeral driver and one ephemeral worker per run, while permitting Spark Standalone to schedule the application's executors across any registered worker. Exclusive driver/worker placement is not required. The functional and service-boundary design artifacts have been updated to reflect this. All Unit 2 NFR answers are resolved.
