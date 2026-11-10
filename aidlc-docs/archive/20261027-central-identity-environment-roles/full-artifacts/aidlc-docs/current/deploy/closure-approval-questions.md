# Intent Closure Decision

Unit 5 isolated Build and Test is complete and its results are in `deployment-handoff.md`. The AI-DLC intent remains open: production StarRocks grants have not been inventoried or migrated, identities have not been cut over, and the MIT KDC remains authoritative. Do not mark production rollout complete.

## Remaining limits

- Unit 2 Build and Test closed with a user-accepted verification waiver. Actual FreeIPA entry membership variants were not tested against the RustFS reconciler.
- Unit 3 passed with documented limits: analyst Hive metadata DDL authorization, FreeIPA group-revocation timing, Hive metadata-cache behavior, and Airflow ETL integration remain unestablished.
- Unit 4's authorization checks deny a fresh spawn after role removal, and no notebook is created. JupyterHub surfaces this expected pre-spawn denial as HTTP 500.
- Unit 5 tests passed on disposable services. Existing production FE users/default grants, catalog collisions, and object ownership remain to be inventoried and reviewed before bootstrap/grant migration.
- The read-only production inventory is now recorded. The current writer has `INSERT`/`UPDATE`/`DELETE` on eight tables in each of two databases, while the tested new role design grants external-source `INSERT` only. The rollout must preserve this behavior or explicitly accept the permission reduction.
- `write-service-account` has a direct StarRocks writer-role exception to support external-source MV refresh. FreeIPA group removal does not revoke that role. FreeIPA disable blocks new logins but leaves existing SQL sessions usable; offboarding must close sessions and revoke the direct role/reset the default role.
- Direct Spark/RustFS policy enforcement is covered by Unit 3 evidence, but was not repeated in Unit 5 because the retained probe launcher attaches to the production network. Unit 3 metadata DDL, group-revocation timing, Hive cache, and Airflow limits remain. No numeric revocation SLA exists.
- Production KDC cutover, production client migration, StarRocks grant migration, and production RustFS policy changes remain pending.

Closing with a waiver records these limits as incomplete; it does not mark them as passing or authorize production deployment. Keeping the intent open allows a separately reviewed cutover plan and remaining checks to be completed.

## Question

How should this intent proceed?

A) Close the AI-DLC intent with a verification waiver. Preserve all limits above in the archive and record that production deployment/KDC cutover remains pending. Prepare a compaction preview for separate review; do not archive or clean up until that exact preview is approved.

B) Keep the intent open. Prepare the next work plan for production cutover and/or the remaining verification items.

C) Other (describe below).

[Answer]: A — Close with a verification waiver. The user explicitly approved closure on 2026-10-28. The listed verification limits and pending production work remain incomplete; no deployment is authorized.
