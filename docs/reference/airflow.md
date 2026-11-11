# Airflow and the DAG factory

Reference: scheduled Spark workloads built from each product repository. Back to the [README](../../README.md).

## Start, stop, and sign in

- **Start and stop**: start it with `./scripts/lakehouse.sh start-airflow`. Use `airflow-status` and `stop-airflow` to check and stop it.
- **Sign-in**: the UI at <http://127.0.0.1:8085> uses Keycloak sign-in. Roles come from each product file's `apps.airflow`, read at every sign-in, and apply to the whole Airflow. The local FAB login is for recovery only and is limited to `AIRFLOW_ADMIN_USERNAME`.

## DAG bundles

Every product with a `repo` block gets two Git bundles, `<name>-main` (its `prod_branch`, production) and `<name>-uat` (its `uat_branch`). `default` has `default-main` and `default-uat` from `opensource-lakehouse-sample-dp`. The bundles are cloned into this repository's `.runtime/airflow-dag-bundles` and refresh every five minutes. `start-airflow` generates the list from `data-products/*.yaml` and checks it.

- Only `<product>-main` (environment `prod`) and `<product>-uat` (`uat`) are accepted. Each bundle checks out `dags`, `workflows`, `notebooks`, and `configs`, plus the files at the repository root (Git always includes them), such as `requirements.txt`. Airflow looks for DAG files only in `dags/` (the bundles' `subdir`), so code under `notebooks/` is never imported by the DAG processor.

## Runs and the writer

- **Runs**: each DAG run starts its own Spark container, with the bundle mounted read-only, and gets its write token from a token broker that keeps all credentials out of DAG code and Spark. The container also gets the run's checkpoint key ([Streaming checkpoints](streaming-checkpoints.md)). All of a run's tasks share that container, so tasks that run at the same time compete for its memory.
- **Which writer**: the broker takes the product from the DAG ID, which must start with the bundle name (`default-main-test_environment` writes as `srv-default-writer`). It then asks Airflow, as the read-only user `lakehouse-broker`, which bundle the DAG really comes from, and refuses the run unless that is the product's own bundle. A refused run fails at `create_cluster` with `unknown_product`, `unknown_dag`, or `bundle_mismatch`.
- **Run length**: a run's broker registration lasts 24 hours; tokens are renewed through it until then.

## Workflow files

A product repository declares DAGs in `workflows/<name>.json` and keeps its code in `notebooks/` and its settings in `configs/` (both also used from Jupyter). Its only DAG file is the stub `dags/lakehouse.py`, which calls the platform factory `infra/airflow/lakehouse_dags` (mounted read-only into the dag-processor and the scheduler). The factory builds `<bundle>-<name>` with `create_cluster`, `install_requirements` (the repository's optional root `requirements.txt`; see [Workload Python environment](workload-python.md)), `validate_environment` (the repository's own `config_loader`, run inside the Spark container), one `submit_<task>` per task in `runs_after` order, `stop_cluster`, and `verify_workloads_succeeded`. No repository code runs in the scheduler, which holds the Docker socket and the broker token.

```json
{
  "apiVersion": "lakehouse.local/workflow/v1",
  "name": "test_environment",
  "schedule": null,
  "tasks": [
    {"name": "load", "entrypoint": "load.py", "args": ["--date", "2026-11-10"], "retries": 2, "retry_delay_seconds": 60},
    {"name": "count", "entrypoint": "count_sample_rows.py", "runs_after": ["load"], "execution_timeout_seconds": 3600}
  ]
}
```

- **Subprojects**: a repository may group workflows by subproject: `workflows/<project>/<name>.json`, with that workflow's entry points in `notebooks/workload/<project>/` (for example `workflows/sample/generate_tpch.json` runs `notebooks/workload/sample/other/generate_tpch.py`). Notebooks may sit in a medallion layer folder of that code folder, `bronze/`, `silver/`, `gold/`, `ops/`, `deploy/` or `other/` (notebooks that fit no medallion layer), named as `"entrypoint": "bronze/load_orders.py"`; workflows themselves have no layer folders. Flat `workflows/<name>.json` files keep using `notebooks/workload/`. DAG IDs stay `<bundle>-<name>`, so a workflow name may appear only once in a repository; a folder name is letters, digits, `_` and `-`, and holds only `*.json` files.
- **Fields**: `apiVersion`, `name` (equal to the file name), `schedule` (`null` or a cron or preset string), optional `description` and `tags`; each task has `name`, `entrypoint` (a file in `notebooks/workload/`, or `notebooks/workload/<project>/` for a subproject workflow; optionally `<layer>/<file>.py` with layer `bronze`, `silver`, `gold`, `ops`, `deploy` or `other`), and optional `runs_after`, `args` (passed after `--` to the entry point, never templated), `retries` (0 to 10), `retry_delay_seconds` (with retries), and `execution_timeout_seconds`. Unknown keys and invalid values are refused.
- **Errors**: one invalid workflow file is an import error for the stub, so none of that bundle's DAGs load until it is fixed. Product CI catches it first: the Jenkins image has `lakehouse-validate-workflows`, which checks the workflows, the exact stub, and that `dags/` holds nothing else, and then a root `requirements.txt` against the platform lock.
- **The repository side**: the detailed structure of a product repository (notebook standard, naming conventions, helpers) is documented in the sample data product repository, [`opensource-lakehouse-sample-dp`](https://github.com/cdiogo1979/opensource-lakehouse-sample-dp).

## Changing the factory and checks

- **Changing the factory**: edits under `infra/airflow/lakehouse_dags` are visible to the containers at once through the mount; apply them with `./scripts/lakehouse.sh start-airflow`, and run `scripts/verify/dag-factory-tests.sh` (inside the Airflow image) first.
- **Checks**: `scripts/verify/airflow-dags.sh` waits for DAGs from every product bundle and warns about DAG IDs without their bundle prefix. `scripts/verify/broker-unit-tests.sh` runs the broker tests inside its image, and `scripts/verify/dag-factory-tests.sh` the DAG factory tests inside the Airflow image.
