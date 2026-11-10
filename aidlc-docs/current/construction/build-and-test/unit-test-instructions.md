# Unit Test Instructions — s3-checkpoints

```sh
python3 -m pytest -q tests
```
New and changed tests: `tests/rustfs/test_checkpoint_keys.py` (P1, fake RustFS), `tests/workload_env/test_spark_session.py` (P3, P4), `tests/jupyterhub/test_checkpoint_key_mounts.py` (P2), `tests/airflow/test_dag_factory.py`, `tests/operations/test_data_product_scripts.py`, `tests/workload_env/test_image_contracts.py`. Properties are derandomized (Hypothesis `derandomize=True`, 200 examples).
Expected: all pass; 3 existing skips.
