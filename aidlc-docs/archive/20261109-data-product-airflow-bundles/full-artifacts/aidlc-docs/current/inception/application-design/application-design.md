# Application Design — Data Product Airflow Bundles

Consolidates [components.md](components.md), [component-methods.md](component-methods.md), [services.md](services.md), and [component-dependency.md](component-dependency.md); the probe is in [application-design-plan.md](../plans/application-design-plan.md).

## Summary
- **Product file**: gains an optional `repo` block. Each product with one gets the Airflow bundles `<name>-main` (prod branch) and `<name>-uat` (UAT branch), generated from the files; `default` is renamed now.
- **Lifecycle**: applying or removing a product recreates Airflow when the bundles or writers changed. Airflow then clones and loads the DAGs, with no run.
- **Broker**: it holds every product writer. A run's DAG ID (`<name>-main-…`/`<name>-uat-…`) names the product. The broker confirms through the Airflow API (a dedicated Viewer user, probed) that the DAG really lives in that product's bundle, and only then issues the product writer's token. DAG code never sees a credential, and a product cannot borrow another's writer.
- **Workload repository**: a patch makes it recognise the new bundle names and read product-specific configs. It is delivered for the user to push.

## Decisions
| Ref | Decision |
|---|---|
| Q1 | DAG-ID prefix plus an Airflow bundle check (probed: Viewer can read `bundle_name` and cannot read Connections or change DAGs) |
| C1/CR-1 | Names from the product `name`; no writer field; the writer is the product's `writer_user` |
| Q3 | default's bundles renamed now; the interim DAG behavior is documented until the patch is pushed |
| Q4 | Register and load only |
| Design | Restarts are driven by a fingerprint of (bundle list, writer set), so an unchanged apply recreates nothing |
| Design | Writer passwords are staged only into a broker-only mount, never as Airflow Connections or environment variables |

## Risks
| Risk | Mitigation |
|---|---|
| default's DAGs misbehave until the workload patch is pushed | Documented; Build and Test records the state; the patch is tested locally against the bundle checkout |
| A recreate interrupts running DAG runs | Only on change; documented; `--no-restart` defers it |
| Airflow API unavailable | The broker refuses registration (`service_unavailable`); runs fail closed, never with a wrong writer |
