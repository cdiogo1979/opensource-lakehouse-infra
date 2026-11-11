# Audit Archive Pointer

The complete audit history through intent `20261111-airflow-task-params` is preserved at `aidlc-docs/archive/20261111-airflow-task-params/full-artifacts/aidlc-docs/current/audit.md`.

## Intent Closure: 20261111-airflow-task-params
**Archive**: `aidlc-docs/archive/20261111-airflow-task-params`
**Summary**: `aidlc-docs/archive/20261111-airflow-task-params/intent-summary.md`

## Workspace Detection — New Intent: 20261111-mv-promotion
**Timestamp**: 2026-11-11T20:30:00Z
**User Input**: "start a new infra intent. this intent may also adjust the data produt repo . a developer should develop and test  MVs in starrocks, but they should be transported to uat and prod as part of the normal process. i see two options , one is deploy notebooks/jobs in airflow , somehow part of the build CI for uat and prod. you may suggest other options"
**AI Response**: "Brownfield; previous intent closed; infra and sample repositories clean on main. Focused read: Jenkins _ci/_cd only validate (no deployment); StarRocks logins are LDAP passwords; the writer role has author on the MV databases in uat and prod (bootstrap grants CREATE MATERIALIZED VIEW); no Airflow run or Jenkins job holds a StarRocks credential; the product repository standard already defines an empty deploy/ layer. Options and questions presented."
**Context**: INCEPTION; workspace detection; APG-03.
**User**: cdiogo1979
**Email**: cdiogo@gmail.com

---

## Requirements Analysis — Answers
**Timestamp**: 2026-11-11T20:45:00Z
**User Input**: "Approach: Declared MV files, platform deploys (Recommended); Login: Probe Keycloak tokens first (Recommended); Removals: Drop it (Recommended); Trigger: With every pipeline run, first (Recommended)"
**AI Response**: "Checked without changes: the scheduler and StarRocks FE share the core network; the Airflow image has pymysql. Requirements FR-1 to FR-7, NFR-1 to NFR-3, probes P1 (JWT login on a throwaway FE) and P2 (MV marker in the live dev MV database), and the plan (two units: platform, sample product) written. Missing source tables are skipped, not failed, because the deploy runs before the tasks. Presented for approval, including the probes."
**Context**: INCEPTION; requirements analysis and workflow planning; APG-03.
**User**: cdiogo1979
**Email**: cdiogo@gmail.com

---

## Requirements Analysis — Change Request CR-1: Two tpch MVs
**Timestamp**: 2026-11-11T20:55:00Z
**User Input**: "as part of this intent you should create two mvs for the tcph , one with all details but current day orders only mv_tcph_current, and the other without order level mv_tcph_aggregated" then "Names: mv_tpch_current, mv_tpch_aggregated (Recommended); Current day: Latest load day (Recommended); Aggregate: the first one but adjust the name of the view to reflect the dimensions kept"
**AI Response**: "FR-7 now holds mv_tpch_current (all details, orders of the latest bronze load day) and mv_tpch_day_nation_segment (per order date, customer region and nation, market segment: orders, lines, quantity, revenue, average discount). Probe P2 also checks that StarRocks accepts both definitions on the Iceberg catalog."
**Context**: INCEPTION; change request; APG-03.
**User**: cdiogo1979
**Email**: cdiogo@gmail.com

---

## Inception Approval
**Timestamp**: 2026-11-11T21:00:00Z
**User Input**: "approve and continue"
**AI Response**: "Requirements (with CR-1) and plan approved, including probes P1 (JWT login on a throwaway StarRocks FE) and P2 (marker and the two tpch definitions in the live dev MV database as joe-developer). Starting P1."
**Context**: INCEPTION approved; APG-03.
**User**: cdiogo1979
**Email**: cdiogo@gmail.com

---

## Probe P1 — JWT Login (throwaway StarRocks FE)
**Timestamp**: 2026-11-11T21:20:00Z
**User Input**: (approved with the requirements)
**AI Response**: "Throwaway FE (starrocks/fe-ubuntu:4.1.7, network core, no ports, no volumes; removed afterwards). The writer's Keycloak token (client lakehouse-writer, iss http://keycloak.localhost:8080/realms/lakehouse, preferred_username srv-default-writer) was obtained in a container from mounted secret files; no secret printed. CREATE USER 'srv-default-writer' IDENTIFIED WITH authentication_jwt AS {jwks_url http://keycloak:8080/.../certs, principal_field preferred_username, required_issuer} succeeded. The server requests the MySQL client plugin authentication_openid_connect_client, which pymysql lacks; with a 10-line handler (capability byte 0x01, length-encoded token) the login succeeded as 'srv-default-writer'@'%'; a malformed token was refused (1045). Consequence: a StarRocks user has one authentication method, so a JWT writer can't also log in with its LDAP password."
**Context**: INCEPTION; probe P1; APG-03.
**User**: cdiogo1979
**Email**: cdiogo@gmail.com

---

## Probe P2 and Application Design
**Timestamp**: 2026-11-11T21:45:00Z
**User Input**: (approved with the requirements)
**AI Response**: "P2 in the live dev MV database as joe-developer (MVs default_lhdev.probe_* reading lakehouse_uat.default_lhuat; all dropped, 0 left): both tpch definitions accepted; information_schema.tables returns the COMMENT marker; no CREATE OR REPLACE and no comment ALTER; REFRESH ... WITH SYNC MODE filled the aggregate (14588 rows, 15000 orders); ALTER MATERIALIZED VIEW ... SWAP WITH is atomic. Broker: re-registering an active run returns a fresh writer token. Application design written: spec checks for MV files, new mv_deploy module, factory task and standalone DAG, writer users switched to JWT, StarRocks CA mounted in the scheduler, sample repository MVs."
**Context**: INCEPTION; probe P2; application design; APG-03.
**User**: cdiogo1979
**Email**: cdiogo@gmail.com

---

## Construction — Code Generation (U1, U2) and Change Request CR-2
**Timestamp**: 2026-11-11T20:30:00Z
**User Input**: "approve and continue" (application design)
**AI Response**: "Functional design folded into the application design (its Rules section states the deploy plan fully); recorded as a deviation. U1 (infra): spec MV file rules (+ reserved workflow name), validator output, mv_deploy module (render, marker, plan, apply with SWAP, OpenID Connect client handler), factory deploy task before the tasks and the on-demand <bundle>-deploy_materialized_views DAG, reconciler: product writers on token login (authentication_jwt) and people on LDAP, scheduler mounts (product files, data_products.py, StarRocks CA, STARROCKS_ENABLED), docs. Probe P2c: a missing source table gives 5502 'Unknown table'. U2 (sample, branch mv-promotion from origin/main, no tracking): materialized_views/tpch/mv_tpch_current.sql and mv_tpch_day_nation_segment.sql, tests, README, AGENTS.md. Tests: infra host 627 passed, 3 skipped (+ staging test); Airflow image 118 passed; StarRocks 49 passed; sample 110 passed, 2 skipped; code quality PASS.
CR-2 (found during live preparation): the scheduled reconciler had failed every cycle since 18:04 UTC with FileNotFoundError on /run/secrets/*: start-airflow re-runs prepare-runtime.py, which replaced unchanged staged mounts (new inode), so the core reconciler's file bind mounts pointed to deleted files. Fixed in prepare-runtime.py, prepare-starrocks-certificates.py and prepare-ldap-certificates.py (an unchanged file is kept); regression test added; reconciler restarted: Polaris principals=6 synced, srv-default-writer switched to token login in place. start-airflow afterwards: the reconciler's secrets stayed readable; the scheduler has the product files, StarRocks CA, pymysql and data_products."
**Context**: CONSTRUCTION; code generation; change request CR-2; APG-03.
**User**: cdiogo1979
**Email**: cdiogo@gmail.com

---

## Construction — Design Questions During Live Checks
**Timestamp**: 2026-11-11T20:45:00Z
**User Input**: "how does it work , do i get a dag by dp and enviroment (uat and main)?" / "do each view shows as inddividual task? will a be able to trigger only a single one, what happens if i run several times the same create statement?" / "what if the ddl of the view needs to be updated?" / "if the process only loads new or changed ddl files then i dont have  an issue"
**AI Response**: "Explained: one deploy DAG per bundle (<product>-uat, <product>-main) when the branch has MV files, plus the deploy step in every workflow DAG; one task for all views; unchanged views (same hash) send no SQL; a changed file is replaced by create-new, SWAP, drop; a failed new definition leaves the current view. Offered per-view tasks, a target option and a synchronous refresh before the swap. User decision: keep the design as is (only new or changed files cause work)."
**Context**: CONSTRUCTION; design confirmation; APG-03.
**User**: cdiogo1979
**Email**: cdiogo@gmail.com

---

## Build and Test — Live Checks
**Timestamp**: 2026-11-11T21:45:00Z
**User Input**: "approve and continue" (live checks, including pushes to the sample repository's uat) / "why is the new dag not showing up?" / "give me a query in uat i can use to test the effect of the mv" / "the explain does not show the use for quety rewrite"
**AI Response**: "Pushed mv-promotion to sample uat (2b8a610). The deploy DAG was missing because bundle checkouts are sparse (dags, workflows, notebooks, configs): added materialized_views to BUNDLE_KWARGS and validate-bundle-config FIXED_KWARGS; start-airflow synced the checkouts. Live: first deploy created both views (writer token login, refresh SUCCESS); repeat unchanged; a pushed interval change replaced mv_tpch_current by swap; a pushed removal dropped the aggregate; a pipeline run deployed as its first step; the revert restored both (same hashes). A failed 'git revert -q' let the pipeline run on the removal commit (harmless; redone). Query rewrite traced: the aggregate is used once fresh; mv_tpch_current is not rewritable (subquery); COUNT(DISTINCT) blocks rollup; documented in data-products.md and the sample README."
**Context**: CONSTRUCTION build and test; APG-03.
**User**: cdiogo1979
**Email**: cdiogo@gmail.com

---

## Deploy — Release, Approval and Intent Closure
**Timestamp**: 2026-11-11T22:05:00Z
**User Input**: "yes proceed"
**AI Response**: "Sample: knowledge (tpch components and D9, repository naming) and the README rewrite note committed; squashed to one commit 925ef51 on top of main and pushed to main and uat. Incident: in the first attempt the staged tree differed by one tracked __pycache__ file (ignored by .gitignore, so 'git add -A' dropped it); the check failed but the chained pushes still ran, and the uat force-push (with lease) reset sample uat to main 5fc4000 for about a minute; no view was dropped (no deploy ran). Corrected with set -e: the file re-added, the tree verified equal to mv-promotion, 925ef51 fast-forwarded main and uat. Closure: canonical airflow-workflows.md, starrocks-sql-access.md, application-design.md updated; functional-design/materialized-view-promotion.md created; manifest with existing artifacts; dry run, then apply. Infra repository changes are not committed."
**Context**: DEPLOY approved; closure; APG-01/APG-03.
**User**: cdiogo1979
**Email**: cdiogo@gmail.com

---
