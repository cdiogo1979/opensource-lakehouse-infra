# Build and Test Summary — Data Product Airflow Bundles

## Outcome: passed, with known items
| Check | Result |
|---|---|
| Contract and property suite | 393 passed, 2 skipped, 1 known failure (Airflow developer-role drift) |
| Broker tests in its image | 11 passed, including P4 |
| Workload repository | 61 passed, lint clean, 1 upstream failure (stale DAG-name assertion) |
| Patch upstream | Committed and pushed to `main` and `uat` of `cdiogo1979/opensource-lakehouse` (`e975471`, then `fedf0bc`), on the user's instruction |
| Bundles | `default-main` and `default-uat` from the `repo` block; `start-airflow` verified DAGs from both and recorded the fingerprint |
| Viewer | `lakehouse-broker`, Viewer only |
| Writer selection | `default-*` DAGs get `srv-default-writer` (`role-default-writer` only); `bttest-*` DAGs get `srv-bttest-writer` (`role-bttest-writer` only); renewals keep the writer; revoke works |
| Refusals | `unknown_product` (`dev-`, `main-` IDs; a removed product), `unknown_dag`; never a token |
| End-to-end | `default-uat-test_environment` run `bt-uat-e2e-1`: all 7 tasks succeeded |
| Create and remove | `bttest` with the same repository: dry run, apply (Airflow recreated, bundles registered), idempotent re-apply ("unchanged"), dry-run removal, removal (Airflow recreated, writer unstaged); fingerprint back to its earlier value (P5 live) |

## Findings fixed during Build and Test
| Finding | Fix |
|---|---|
| Before the workload patch, both bundles built the same DAG ID `dev-test_environment`; `default-uat` showed no DAG and the `start-airflow` check timed out (nothing recorded) | Patch pushed to `main` and `uat`; README states the dependency |
| The patch's new comment in `notebooks/common/job_runtime.py` mentioned "DAG" in a file that mentions "airflow", so Airflow's safe-mode parser imported it as a DAG file (import error in both bundles) | Comment reworded (`fedf0bc`); import errors gone after the next refresh |

## Not run
- A live `bundle_mismatch`: the factory always prefixes DAG IDs with their own bundle, so no such DAG exists; covered by the broker tests (P4).
- A DAG run of `default-main-test_environment` (production) and of `bttest` DAGs (`bttest` had no product configs, so its workload would use the shared configs); writer selection for both was verified through the broker.

## Residue
- The user deleted the `bttest-*` DAG records. `dev-test_environment` (built from `00b6623` before the patch) is still listed under `default-main`, marked stale; the broker refuses it.
- The UAT smoke run `bt-uat-e2e-1` is in Airflow's history.
