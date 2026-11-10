# Code Summary — s3-checkpoints

## Modified
- `infra/spark-runtime/Dockerfile`: `hadoop-aws` 3.3.4 and `aws-java-sdk-bundle` 1.12.262 via `maven-dependency-plugin:3.8.1:copy --strict-checksums`, copied to `/opt/spark/jars/` (the Jupyter image inherits `/opt/spark`).
- `infra/workload-python/python/lakehouse_spark.py`: `ResolvingFileIO` for every catalog; `CheckpointKey`, `parse_checkpoint_key`, `checkpoint_key_files`, `checkpoint_settings`; `create_spark_session` merges them (R14 to R18).
- `infra/airflow/lakehouse_dags/factory.py`: `_checkpoint_key_volume` (one key per run, checked before the broker registration); `_create_spark_container` mounts it (R11, R13).
- `infra/jupyter/hub/lakehouse_policy.py`: `checkpoint_buckets`, `checkpoint_key_volumes` (R12, R13).
- `infra/jupyter/hub/lakehouse_spawner.py`, `jupyterhub_config.py`: `checkpoint_keys_host_dir`; the dev key mounts in `check_current_admission`.
- `compose.airflow.yml`, `compose.jupyter.yml`: the host folder variable and read-only folder mounts.
- `scripts/lakehouse.sh`: `prepare_checkpoint_keys` (create folder, check staged keys), `rotate-checkpoint-keys`, host folder exports.
- `scripts/bootstrap-default-product.sh`, `scripts/operations/create-data-product.sh`, `remove-data-product.sh`: key bootstrap after policies; removal before buckets.
- `README.md`: "Streaming checkpoints" section, bootstrap list, rotation, scripts table.
- Tests: `tests/workload_env/test_image_contracts.py`, `test_spark_session.py` (P3, P4), `tests/airflow/test_dag_factory.py`, `tests/operations/test_data_product_scripts.py`, `test_compose_modules_contract.py`, `tests/rustfs/strategies.py`.

## Created
- `infra/rustfs/bootstrap-checkpoint-keys.py`: converge, rotate, remove, prune, `--check-staged`, `--list`; the `.buckets.json` index (R1 to R10).
- `infra/spark-bootstrap/verify_checkpoint_stream.py` and `scripts/verify/checkpoint-stream.sh`: the two-session stream check, plus fail-closed for another bucket.
- `scripts/verify/checkpoint-keys.py`: allowed and refused cases per staged key, including the cross-product case.
- Tests: `tests/rustfs/test_checkpoint_keys.py` (P1), `tests/jupyterhub/test_checkpoint_key_mounts.py` (P2).

## Deviations from the plan and design (for review)
1. **Bucket index for Airflow**: the Airflow scheduler (which runs the tasks) has no product model. Instead of mounting it there, C3 stages `.buckets.json` (product -> environment -> bucket, no secrets) next to the keys, and the factory reads it. The Hub uses the product model it already loads.
2. **R20 at `start`**: the first `bootstrap-default-product.sh` runs `lakehouse.sh start` before any key exists, so `start` only warns. `start-airflow` refuses to start without staged keys. Both create the staging folder before Compose mounts it, so Docker never creates it.
3. **Stream verifier location**: the Spark app sits next to `create_smoke_tables.py` in `infra/spark-bootstrap/` (it reuses the writer token helper); the runner is `scripts/verify/checkpoint-stream.sh`.
4. **P3 and P4** live in `tests/workload_env/test_spark_session.py`, which holds the other `lakehouse_spark` properties. The planned properties file covers only the lock rules.
5. **Platform administrator**: gets no dev checkpoint key in Jupyter (not an owner or developer group), per R12.

## Local checks (Step 9)
- `python3 -m pytest -q tests`: 581 passed, 3 skipped (the existing skips).
- `ruff`, `flake8`, `bandit` on the changed Python files: nothing new. Existing findings remain in `jupyterhub_config.py`, the spawner import order and `lakehouse_policy.py`. The new scripts' shebang and `noqa` match the existing bootstrap scripts.
- `bash -n` on the changed shell scripts passes. `shellcheck` is not installed.
- Not run here (Build and Test): image builds, the live bootstrap, both verifiers, an Airflow run and a Jupyter session.
