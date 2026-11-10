# Application Design Plan — Data Product Airflow Bundles

## Plan
- [x] Read the requirements (incl. CR-1), reverse engineering, and the canonical designs
- [x] Probe the Airflow 3.3.2 API (throwaway Viewer user, removed)
- [x] Generate components.md, component-methods.md, services.md, component-dependency.md, application-design.md
- [x] Validate against FR-1..FR-6

## Probe results (2026-11-09)
| Question | Result |
|---|---|
| Does Airflow expose a DAG's bundle? | Yes. `GET /api/v2/dags/{dag_id}` returns `bundle_name` (`main-test_environment` → `lakehouse-main`) |
| Can a read-only identity use it? | Yes. A local FAB user with the **Viewer** role gets a token from `POST /auth/token` (201) and reads DAGs (200). Changing a DAG is refused (403), and so is reading Connections (403); an unknown DAG gives 404 |
| Can the broker reach the API? | Yes. The broker and `airflow-api-server` share the `core` network (`http://airflow-api-server:8080`) |
| Current DAG IDs | `main-test_environment`, `uat-test_environment` (prefix `main`/`uat` plus `-` plus the workload), so the renamed form is `default-main-test_environment` |

## Design questions
None needed. The broker's Airflow identity follows the probe: a dedicated Viewer user with its password in a protected file.
