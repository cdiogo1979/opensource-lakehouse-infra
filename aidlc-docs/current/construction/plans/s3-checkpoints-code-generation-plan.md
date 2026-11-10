# Code Generation Plan — s3-checkpoints

The single source of truth for Code Generation of this unit. Workspace root: `/Users/carlosdiogo/code_repo/opensource-lakehouse-infra` (brownfield; files are modified in place).

## Unit context
- **Unit**: `s3-checkpoints` (the only unit); no user stories (skipped). Traceability is to requirements FR-1 to FR-6 and NFR-1 to NFR-5 (CR-1), and to Functional Design rules R1 to R20 and properties P1 to P4.
- **Dependencies**: product model (`infra/products/data_products.py`), RustFS admin API, the existing broker and spawner mounts. No other unit.
- **Owned entities**: checkpoint policy, user and key per product environment bucket (`domain-entities.md`).

## Steps
- [x] **Step 1 — Spark images (C1; FR-1, NFR-4)**: `infra/spark-runtime/Dockerfile` copies `org.apache.hadoop:hadoop-aws:3.3.4` and `com.amazonaws:aws-java-sdk-bundle:1.12.262` with the existing `maven-dependency-plugin:3.8.1:copy` step (`--strict-checksums`) and puts both in `/opt/spark/jars/`. Confirm that `infra/jupyter/singleuser/Dockerfile` inherits them through `/opt/spark`. Tests: extend `tests/workload_env/test_image_contracts.py` (pinned coordinates, strict checksums, jars in `/opt/spark/jars`).
- [x] **Step 2 — Platform Spark session (C2; FR-1, FR-2, NFR-3; R14 to R18)**: `infra/workload-python/python/lakehouse_spark.py`:
  - `io-impl` becomes `ResolvingFileIO`;
  - new `CheckpointKey`, `checkpoint_key_files()` and `checkpoint_settings()`;
  - `create_spark_session` merges them.

  Tests: `tests/workload_env/test_spark_session.py` (settings, invalid files, absent folder, no global key); PBT P3 and P4 in `tests/workload_env/test_workload_python_properties.py`.
- [x] **Step 3 — RustFS checkpoint keys (C3; FR-2, FR-4, NFR-1, NFR-2; R1 to R10)**: new `infra/rustfs/bootstrap-checkpoint-keys.py` (policy, user, attach, authenticate check, rotate, remove, stage, `--product`, `--dry-run`, `--list`, `--check-staged`), reusing `S3Client` and `read_secret` from `bootstrap-buckets.py`. Tests: new `tests/rustfs/test_checkpoint_keys.py` (fake admin client: converge, idempotence, rotate order, remove order, file modes, stale staged files, no secret in output); PBT P1 in it, with generators added to `tests/rustfs/strategies.py`.
- [x] **Step 4 — Airflow DAG factory (C4; FR-4; R11, R13)**: `infra/airflow/lakehouse_dags/factory.py`: `_checkpoint_key_volume(product, environment)` and the extra volume in `_create_spark_container`. `compose.airflow.yml`: `LAKEHOUSE_CHECKPOINT_KEYS_HOST_DIR` and the read-only folder mount `/run/secrets/checkpoint-keys` on the services that run tasks. Tests: `tests/airflow/test_dag_factory.py` (exactly one key, the run's bucket; missing or symlinked file fails before creating a container).
- [x] **Step 5 — JupyterHub spawner (C5; FR-4; R12, R13)**: `infra/jupyter/hub/lakehouse_spawner.py`: `checkpoint_buckets(groups, products)` and the volumes in `check_current_admission`. `jupyterhub_config.py` and `compose.jupyter.yml`: `JUPYTERHUB_CHECKPOINT_KEYS_HOST_DIR` and the read-only folder mount. Tests: new `tests/jupyterhub/test_checkpoint_key_mounts.py` (owner and developer get `dev` keys; analysts and writers get none; missing file fails the spawn); PBT P2.
- [x] **Step 6 — Platform operations (C6; R5, R20)**:
  - `scripts/bootstrap-default-product.sh` and `scripts/operations/create-data-product.sh` run C3 after `bootstrap-policies.py`;
  - `remove-data-product.sh` runs C3 `--remove` before `bootstrap-buckets.py --remove`;
  - `scripts/lakehouse.sh` exports the host folder paths, runs the R20 check in `start` (Jupyter enabled) and `start-airflow`, and adds `rotate-checkpoint-keys [--product P]`;
  - check that `scripts/operations/reset-lakehouse.py` clears the new `.runtime` folders together with the RustFS users.

  Tests: `tests/operations/test_data_product_scripts.py` and `test_compose_modules_contract.py` (ordering and wiring).
- [x] **Step 7 — Verification (C7; FR-6)**:
  - new `scripts/verify/checkpoint-keys.py`: per staged key, allowed and refused operations, including the cross-product case, printing status codes only;
  - new `scripts/verify/checkpoint-stream.py`: Iceberg availableNow stream from the smoke table into a `noop` sink with an `s3ckpt://` checkpoint, run twice in separate sessions, expecting resume with no reprocessing; the checkpoint is deleted afterwards.
- [x] **Step 8 — Documentation (FR-5; R19)**: platform `README.md` gets a "Streaming checkpoints" section covering `checkpoint_path`, the `s3ckpt://` scheme, key delivery in Airflow and Jupyter, rotation, limits and the Iceberg `streaming-skip-*` options. Code summary in `aidlc-docs/current/construction/s3-checkpoints/code/summary.md`.
- [x] **Step 9 — Local checks**: run the affected test folders (`tests/workload_env`, `tests/rustfs`, `tests/airflow`, `tests/jupyterhub`, `tests/operations`) and the repository's code-quality checks on the changed files. Report the results as they are.

## Not in this stage
Image builds, running the bootstrap against the live stack, and the verifiers run in Build and Test. Deploy is a handoff.
