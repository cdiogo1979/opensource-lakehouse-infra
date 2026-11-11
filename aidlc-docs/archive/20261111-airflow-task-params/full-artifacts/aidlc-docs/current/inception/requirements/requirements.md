# Requirements — Airflow Task Parameters

Depth: standard (small change, but trigger-time values reach product code).

## Request
"lets start a small paltform intent , for enabling the task parameters in aiflow"

## Answers
- Declaration: "take the example of tcph workflow. could i not just a run where i set the parameter for one of the tasks?" — clarified: **per task, at trigger time, by task name**, in the same shape as a notebook's `TASK_ARGS_VALUES`; nothing declared in the workflow.
- Values: **printable strings, length-limited**.
- Overlap: **the trigger value replaces** the workflow's value for the same option.
- Sample repository: **separate small intent later** (silver lookback as a trigger value instead of a temporary workflow edit).

## Functional requirements
- **FR-1** Every factory-built DAG has one param, `task_args`, an object that defaults to `{}`, shown in Airflow's trigger form with a description listing the DAG's task names. Scheduled runs and triggers without it run exactly as today.
- **FR-2** Shape: `{"<task name>": {"<argument name>": "<value>"}}`, for example `{"tpch_region_load": {"silver_lookback_days": "7"}}`. Task names must be tasks of this workflow; argument names follow the job parser's rule (`[a-z][a-z0-9_]{0,49}`); values are printable strings of 1 to 500 characters; at most 20 arguments per task.
- **FR-3** Rendering: each value becomes one token `--<name with - for _>=<value>` appended after that task's workflow `args`; any occurrence of the same option in the workflow `args` (`--opt value` or `--opt=value`) is removed first, so the trigger value replaces it. Other tasks are unchanged.
- **FR-4** Validation happens before anything starts: an invalid `task_args` fails `create_cluster`, naming every problem, and no Spark container is created. The job's own parser still checks which options it accepts (an unknown option fails that task, as today).
- **FR-5** Each submit task logs its workflow arguments and its effective arguments.
- **FR-6** Docs: the Airflow reference page and the developer journey describe triggering with `task_args`; the workflow JSON format is unchanged.

## Non-functional and security
- **NFR-1 (no templating)** Values are never rendered by Jinja, never shell-interpreted, and never read Airflow connections or variables; `template_fields` stays empty.
- **NFR-2 (one token per value)** A value can never become a separate option or the `--` separator: it is always inside its own `--name=value` token.
- **NFR-3 (who can set values)** Anyone who may trigger a DAG may set `task_args`; Airflow roles are platform-wide (existing limitation), so this is documented, not changed.
- **NFR-4** Tests: unit tests for validation and rendering; a property test that rendering then parsing with the sample repository's parser rules returns the trigger values, that replaced options appear once, and that other tasks are untouched.

## Extensions
Security Baseline: enabled (input validation, no injection, logging). Property-Based Testing: enabled. Resiliency: no.
