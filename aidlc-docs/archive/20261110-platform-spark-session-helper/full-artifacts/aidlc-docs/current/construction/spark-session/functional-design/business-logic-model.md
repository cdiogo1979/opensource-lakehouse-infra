# Business Logic Model — spark-session

## Flows
1. **Airflow task**: `spark-submit job.py --environment uat --config-dir … -- --entity orders` → `start_spark_job`: `parse_args` → config (product folder or shared) → `create_spark_session("uat-job", catalog_name)` (BR-S3 airflow) → the job calls `parse_task_args(DECLARATION)` → `{"entity": "orders", "scale_factor": "0.01"}`.
2. **Jupyter notebook**: `%env LAKEHOUSE_ENVIRONMENT=uat` (optional) → `WIDGET_LIST = [...]` and `%run ../common/jupyter_input_widget_helper.py` (optional) → `%run ../common/jupyter_environment_resolver.py` → `spark`, `config` → the user types in the widgets → the job cell calls `parse_task_args(DECLARATION)` → values from the widgets (else `TASK_ARGS`).
3. **Rerun in a kernel**: the resolver returns the same session (same catalog); a different environment's catalog raises the restart error.

## Failure behavior
| Situation | Result |
|---|---|
| Airflow settings incomplete | `RuntimeError` naming the missing variables; the task fails, cleanup runs |
| No token source | `RuntimeError` |
| Unknown catalog in the config | `ValueError` |
| Bad `LAKEHOUSE_ENVIRONMENT` in Jupyter | `ValueError` before Spark starts |
| Structural argument problem | every problem and the usage; exit 2 in Airflow, `TaskArgumentError` in Jupyter |
| Bad `WIDGET_LIST` or `TASK_ARGS` | `ValueError` / a reported problem, nothing changed |
| Notebook outside a clone | `FileNotFoundError` |

## Testable properties (PBT-01)
| # | Property | Category | Rules | Where |
|---|---|---|---|---|
| P1 | For every catalog, `catalog_settings` sets all three catalogs with the eight keys, that default catalog, and redaction; no value contains a token-like string | invariant | BR-S1, BR-S2 | platform |
| P2 | `select_token_source` agrees with a reference decision table over generated environments (provider value, present and missing variables) | oracle | BR-S3 | platform |
| P3 | Rendering generated declared values as task arguments (any order, space or `=` form) and parsing them gives the same values, with defaults for the rest | round-trip | BR-A2, BR-A5 | repository |
| P4 | The same values through widgets, through `TASK_ARGS` and through the command line give the same result | invariant (equivalence) | BR-A4 | repository |
| P5 | Adding an undeclared option, a repeat, or dropping a required option always yields an error that names it, never a result | invariant | BR-A3 | repository |
| P6 | Option names: the mapping `name → --option` is injective over valid declarations, and parsing is idempotent on the rendered form | idempotence | BR-A1 | repository |
| P7 | Only `dev`, `uat`, `prod` (and unset) are accepted for the Jupyter environment | invariant | BR-J2 | repository |

**Generators (PBT-07)**: declarations from valid names (letters, digits, underscores) with required/default/none specs; values as printable strings including spaces, `=`, leading `-` (for the `=` form); environment maps built from the real variable names. **Framework (PBT-08, 09)**: Hypothesis, derandomized or seeded as each repository already does, with `print_blob`.
**Not property-tested**: Spark itself, the Hub broker call, widget rendering (verified live).
