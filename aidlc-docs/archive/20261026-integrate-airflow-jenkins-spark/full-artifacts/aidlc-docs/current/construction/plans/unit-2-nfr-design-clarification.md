# Unit 2 NFR Design — Shared Worker Cleanup Clarification

The approved requirements allow Spark Standalone to schedule any application's executors on any registered worker. Each DAG run also owns an ephemeral worker that must be removed within 60 seconds after that DAG reaches a terminal state.

These rules can conflict: the worker owned by a completed run may still be executing tasks for another active Spark application. Removing it can terminate those executors and may cause task retries or another run to fail. The current requirements do not specify whether this disruption is acceptable.

## Question — What should happen when another run is using the worker?

A) **Keep the 60-second cleanup deadline.** Decommission and remove the completed run's worker within 60 seconds even if it still hosts another application's executors. Accept executor loss; Spark may retry work, and the other Airflow run may fail and use its configured retry behavior. No guarantee is made that another active run is unaffected.

B) **Protect other active runs.** Change the design to prevent cross-run executor placement, for example by isolating each run from the shared worker pool. This revises the approved shared-scheduling behavior and requires deciding whether a dedicated master or another explicit placement mechanism is acceptable.

C) **Drain before removal.** Keep the shared scheduling model, but defer removal of a run's worker until no other active application is using it. This revises the 60-second cleanup requirement; specify the maximum acceptable wait and what should happen if the worker remains in use.

**[Answer]:** C — wait 60 seconds and apply timeout handling.

## Resolution

- At run completion, decommission its worker so Spark Standalone does not assign new executors there.
- Wait for executors belonging to other active applications to leave within the same 60-second paired-cleanup deadline; drain time does not extend that deadline.
- If executors remain at the deadline, stop and remove the worker to preserve the approved paired-container cleanup deadline. Emit a sanitized `worker_drain_timeout` event identifying the affected run IDs where available; the event warns that executor loss may cause another run to retry or fail.
- Preserve the original workload result if cleanup also reports a drain timeout. The cleanup task records the drain timeout separately and continues stopping/removing run-scoped containers.

This interprets the requested timeout as bounded drain within the existing 60-second cleanup budget, followed by forced removal at that same deadline. Cross-run interruption remains possible at the deadline and must be visible; exclusive worker placement is still not required.

**Status**: Clarification resolved; NFR Design artifacts may proceed.

C , 60 seconds wait and timeout
