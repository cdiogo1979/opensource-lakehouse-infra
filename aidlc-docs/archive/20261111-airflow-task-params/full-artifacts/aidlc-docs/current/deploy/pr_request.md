# PR request — Trigger-time task arguments in Airflow

## Problem
A task's arguments could only come from its workflow file, so a one-off run with a different value (for example a silver lookback) meant a temporary workflow edit, a merge, a run and a revert.

## Solution
- **`task_args` param** on every factory-built DAG, empty by default, shown in the trigger form with the DAG's task names. Values per task name, for example `{"tpch_region_load": {"silver_lookback_days": "7"}}`.
- **Rendering**: each value becomes one `--<name>=<value>` token after the task's workflow `args`, replacing the same option there; other tasks run as written. No Jinja, no shell.
- **Validation** before anything starts: an invalid `task_args` fails `create_cluster` with every problem named, before the run is registered or a container is created.
- **Logging**: each task logs its workflow and effective arguments (redacted).
- New `infra/airflow/lakehouse_dags/task_args.py`; `factory.py` wiring; tests; `docs/reference/airflow.md` and the developer journey.

## Verification
Host pytest 608 passed, 3 skipped; Airflow-image tests 81 passed; property test over render-then-parse. Live in UAT: a run with `{"tpch_region_load": {"silver_lookback_days": "1"}}` succeeded with that task's effective arguments and `lookback_days: 1`, other tasks unchanged; a run with an unknown task and a non-string value failed at `create_cluster` with no container.

## Deployment
Applied with `./scripts/lakehouse.sh start-airflow` (done).

## Risks and limitations
Anyone who can trigger a DAG can set `task_args` (Airflow roles are platform-wide). The job's own parser decides which options it accepts.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
