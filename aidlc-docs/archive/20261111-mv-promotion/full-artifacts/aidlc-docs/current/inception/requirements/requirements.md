# Requirements — Materialized View Promotion

Depth: standard (new platform capability; a pipeline gains StarRocks write access in uat and prod).

## Request
"a developer should develop and test MVs in starrocks, but they should be transported to uat and prod as part of the normal process" (options: deploy notebooks/jobs in Airflow, CI; others welcome).

## Answers
- Approach: **declared MV files in the product repository, deployed by the platform** (product code never holds a StarRocks login).
- Login: **probe Keycloak tokens (JWT) first**; fallback: the platform reads the writer's password file server-side.
- Removals: **drop** managed MVs whose file is gone; never touch MVs created by hand.
- Trigger: **with every pipeline run, first**, plus a standalone deploy DAG.

## Functional requirements
- **FR-1 Definitions**: a product repository may hold `materialized_views/<project>/<name>.sql`, one `CREATE MATERIALIZED VIEW ${mv_database}.<name> ...` statement per file (the file name is the MV name, unique in the repository). Placeholders `${catalog}`, `${namespace}` and `${mv_database}` stand for the environment's values from the product file; nothing else is substituted and nothing is templated.
- **FR-2 Develop and test in dev**: developers author the same statement by hand in the dev MV database (their `author` level), with the dev values; the README shows how to turn a tested dev statement into the file.
- **FR-3 CI**: `lakehouse-validate-workflows` (Jenkins `_ci` and `_cd`) also checks the MV files: folder and name rules, exactly one `CREATE MATERIALIZED VIEW` statement, the target `${mv_database}.<file name>`, only the three placeholders, no other statements.
- **FR-4 Deploy as the writer**: a platform task, `deploy_materialized_views`, connects to StarRocks as the product's writer (over TLS) and, for the bundle's environment: creates MVs that don't exist; replaces MVs whose definition changed; drops managed MVs whose file is gone; leaves unchanged and hand-made MVs alone. Managed MVs carry a marker (with a definition hash) so the task can tell them apart.
- **FR-5 When**: every factory-built workflow DAG runs `deploy_materialized_views` after `validate_environment` and before its tasks; an MV whose source table doesn't exist yet is reported and skipped (created by a later run), not failed. A standalone DAG `<bundle>-deploy_materialized_views` runs it on demand. Bundles without MV files get no deploy task.
- **FR-6 Logging**: each deploy logs what it created, replaced, dropped, skipped and left unchanged.
- **FR-7 Data product repository** (sample): two tpch MVs, their files, tests, README and AGENTS.md rules:
  - **`mv_tpch_current`**: all details (order, line items, customer, nation, region, part, supplier) for the orders of the **latest load day**: orders whose silver row has `DATE(bronze_ingestion_timestamp)` equal to the newest such day in `tpch_orders`;
  - **`mv_tpch_day_nation_segment`** (no order level; named for the dimensions it keeps): per `o_orderdate`, customer region and nation, and `c_mktsegment`: order count, line count, quantity, revenue (`l_extendedprice * (1 - l_discount)`) and average discount.

## Non-functional and security
- **NFR-1** The StarRocks login is the writer's, used only by platform code in the scheduler; no product code and no Spark container receives it. Authorization stays StarRocks' own: the writer can create only in its MV databases and read only its namespaces.
- **NFR-2** No credential in logs; TLS to StarRocks.
- **NFR-3** Property tests: placeholder substitution and statement checks; the deploy plan (create, replace, drop, keep) over generated repository and database states.

## Change requests
- **CR-1** (user, during requirements): the two tpch MVs of FR-7 (names `mv_tpch_*`; "current day" is the latest load day; the aggregate at day x nation x segment, named for its dimensions).

## Probes before design
- **P1** Can StarRocks 4.1.7 log in a user with a Keycloak-issued JWT (the writer's token from the broker), and how does that combine with the existing LDAP logins? Run on a throwaway StarRocks frontend container, so the live StarRocks is not changed.
- **P2** Can an MV carry the marker (a `COMMENT` or property) that `SHOW` or `information_schema` returns, can it be replaced in place, and does StarRocks accept the two FR-7 definitions on the Iceberg catalog (the latest-load-day filter is a subquery)? Run in the live dev MV database as a developer, creating and dropping one probe MV.
