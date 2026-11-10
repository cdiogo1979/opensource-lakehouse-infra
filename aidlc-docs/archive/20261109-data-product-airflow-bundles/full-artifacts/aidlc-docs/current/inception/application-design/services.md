# Services — Data Product Airflow Bundles

## S1 `lakehouse.sh start-airflow`
1. `prepare-runtime.py` and the Airflow secrets, including the `lakehouse-broker` Viewer password.
2. Stage the writers (C3); generate the bundle list (C2); validate with `--host-paths`.
3. Start or recreate the Airflow services. `airflow-init` also runs `ensure-broker-viewer.py`.
4. Verify that each product's bundles are registered (C7).
5. Record the fingerprint in `.runtime/state/airflow-bundles.json`.

## S2 Apply or remove a product (existing operator scripts)
After the existing steps (and before recording the product state):
- If Airflow is running and the bundle list or writer set changed: `start-airflow` (S1), unless `--no-restart`, which prints the command.
- If Airflow is not running: nothing. The next `start-airflow` picks up the change.
- `--dry-run`: print the bundle changes.

## S3 A DAG run's token (broker)
`register_run(dag_id, run_id)`:
1. resolve the product from the DAG ID
2. verify the bundle with Airflow
3. issue the product writer's token
4. bind the registration to that product

Renewals reuse the product's writer. Every refusal is logged by reason, without secrets.
