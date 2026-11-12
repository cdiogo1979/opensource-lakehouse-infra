# Functional Design — Workload Python Environment

Current functional design of the shared Python environment that runs workload code in Airflow's Spark containers and in the Jupyter kernel, and of product extras. For architecture, see [`../application-design.md`](../application-design.md). History is in the [Shared Workload Requirements intent archive](../../../archive/20261110-shared-workload-requirements/intent-summary.md) and the [Spark S3 Checkpoints intent archive](../../../archive/20261111-spark-s3-checkpoints/intent-summary.md).

## Responsibility
One pinned Python 3.10 environment, identical in `local/lakehouse-spark-runtime` and `local/lakehouse-jupyter-singleuser`, plus a product's optional extras, which can add packages but never change a pinned version, and the platform's Spark session module that workload code starts Spark with.

| Path | Role |
|---|---|
| `infra/workload-python/requirements.in` | Top-level pins: PyYAML 6.0.2, requests 2.32.3, pandas 2.2.3, numpy 1.26.4, pyarrow 17.0.0, ipykernel 6.29.5, jupytext 1.16.7, ipywidgets 8.1.9 |
| `infra/workload-python/requirements.lock` | Every package, `name==version`, generated (56 packages on 2026-11-10, with `jupyterlab_widgets` 3.0.17 and `widgetsnbextension` 4.0.16) |
| `infra/workload-python/python/lakehouse_spark.py` | The Spark session for workload code (see "Spark sessions") |
| `infra/workload-python/python/lakehouse_broker_client.py` | The JupyterHub user's token from the Hub broker |
| `infra/workload-python/lakehouse-platform.pth` | `/opt/lakehouse/python` on the venv's path |
| `infra/workload-python/workload_python.py` | Standard-library module and CLI: `check-lock`, `check-venv`, `check-extras`, `install-extras` |
| `scripts/setup/lock-workload-python.sh` | Regenerates the lock in the runtime's base image (digest read from `infra/spark-runtime/Dockerfile`), wheels only, and validates it before writing |
| `scripts/verify/workload-python-parity.sh` | Both images: venv equals the workspace lock, identical `pip freeze`, one Jupyter kernel |

## Environment
- **Location**: `/opt/lakehouse/venv` (Python 3.10.16) in both images, with `/opt/lakehouse/requirements.lock` and `/opt/lakehouse/workload_python.py`. `PYSPARK_PYTHON` and `PYSPARK_DRIVER_PYTHON` point at the venv; in the runtime image the venv is first on `PATH`.
- **Spark runtime**: the venv is built from the base image's `/usr/local/bin/python3` (Debian 11, glibc 2.31). The base image's own packages stay in `/usr/local` and are not visible to workload code.
- **Jupyter**: Python 3.10.16 from conda-forge at `/opt/lakehouse/python3.10` (not on `PATH`), built with `HOME=/root`; JupyterLab stays on conda's Python 3.13. The only kernel is `python3`, display name "Lakehouse (Python 3.10)", on the venv (`kernel.json`); `/etc/jupyter/jupyter_server_config.d/lakehouse-kernels.json` sets `KernelSpecManager.ensure_native_kernel = false` and leaves the base image's `jupyter_server_config.py` in place. The image also has `git` and `jupyterlab-git` 0.55.0 (with `nbdime`).
- **PySpark**: from `/opt/spark/python` (Spark 3.5.5), never from pip.
- **Hadoop S3A**: `hadoop-aws` 3.3.4 and `aws-java-sdk-bundle` 1.12.262 in `/opt/spark/jars` of the runtime image (Maven `--strict-checksums`; they match the image's Hadoop client 3.3.4), inherited by the Jupyter image with `/opt/spark`. Used only for streaming checkpoints (see "Streaming checkpoints").
- **Platform modules**: `/opt/lakehouse/python` in both images, on the venv's `sys.path` through `lakehouse-platform.pth`, whatever `PYTHONPATH` is (Airflow run containers set it to the bundle only). Both builds check the import. Jupyter's `PYTHONPATH` is `/opt/spark/python` and py4j only. JupyterLab has `jupyterlab_widgets` 3.0.17, matching the kernel's.

## Spark sessions
- **`create_spark_session(app_name="lakehouse-user", catalog=None)`**: the default catalog is the argument, else `LAKEHOUSE_POLARIS_CATALOG`, else `lakehouse`, and must be `lakehouse`, `lakehouse_uat` or `lakehouse_dev` (`ValueError`). The application name has 1 to 100 printable characters.
- **Settings** (`catalog_settings`): for each of the three catalogs, `SparkCatalog`, `rest`, `http://polaris:8181/api/catalog`, warehouse = catalog, `LakehouseTokenAuthManager`, `io-impl` `org.apache.iceberg.io.ResolvingFileIO` (since 2026-11-11; it sends `s3`, `s3a`, `s3n` paths to `S3FileIO` with vended credentials and other schemes to `HadoopFileIO`), `Polaris-Realm: lakehouse`, vended credentials, and `rest-metrics-reporting-enabled=false` (no Spark scan or commit reports to Polaris; the report of a table-creating write used to log a misleading warning); plus the Iceberg extensions, the default catalog, and the redaction pattern `(?i)secret|password|token|access[.]?key|credential` for Spark and Spark SQL. No setting holds a token. `spark-defaults.conf` holds only the extensions and the same redaction.
- **Token source** (`select_token_source`): `LAKEHOUSE_TOKEN_PROVIDER=airflow` requires the initial token, broker URL and CA, run handle and capability (missing names are listed, never values); `jupyter`, or unset with `JUPYTERHUB_API_TOKEN`, requests the user's token from the Hub broker and sets the provider variables; anything else is an error. No fallback between them.
- **Checkpoint settings** (`checkpoint_settings`, merged by `create_spark_session`; see "Streaming checkpoints").
- **Quiet logs**: after the session starts, `_quiet_known_warnings` sets `QUIET_LOGGERS` (`CheckpointFileManager`, `ResolveWriteToStream`, Hadoop `MetricsConfig`) to ERROR through log4j; if log4j is unavailable, logging is left unchanged. No log configuration file is shipped, so Airflow's log levels are unchanged. Hadoop's `NativeCodeLoader` line logs at JVM start and remains.
- **Existing session**: returned when its default catalog matches; otherwise a `RuntimeError` asks for a kernel restart.
- **Product repositories** (`opensource-lakehouse-sample-dp` from `ad1ca8d`): `notebooks/common/job_runtime.start_spark_job(app_name)` loads `configs/<env>.yml` and calls `create_spark_session("<env>-<app_name>", config["catalog_name"])`; see `airflow-workflows.md` for the rest of the repository contract.

## Streaming checkpoints
Structured Streaming checkpoints live in the product's own environment bucket, under `checkpoints/`, addressed as `s3ckpt://<bucket>/checkpoints/...`.
- **Why a dedicated scheme**: Iceberg 1.10.2's streaming source reads and writes `<checkpoint>/sources/0/offsets/0` through the *source table's* FileIO, whose Polaris-vended credentials cover only the table location. With `ResolvingFileIO`, `s3ckpt://` goes to `HadoopFileIO` and from there to S3A with the checkpoint key, while table data keeps `S3FileIO` and vended credentials. `s3://` and `s3a://` are deliberately not mapped to S3A.
- **Product contract**: `checkpoint_path: s3ckpt://<bucket>/checkpoints` in `configs/<env>.yml` (the product's own bucket for that environment); each stream appends its own subpath, such as `<project>/<target_table>`, as `checkpointLocation`.
- **Key files** (`checkpoint_key_files`): every entry of `/run/secrets/lakehouse-checkpoints/` must be a regular file (not a symlink) named after a bucket (`^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$`), holding a JSON object with exactly `access_key` (= `ckpt-<bucket>`) and a non-empty `secret_key` (`parse_checkpoint_key`). Anything else stops session creation with an error naming the file, never its content. An absent folder means no keys. `CheckpointKey`'s repr never shows the secret.
- **S3A settings** (`checkpoint_settings`), always set: `fs.s3ckpt.impl=S3AFileSystem`, endpoint `http://rustfs:9000`, `endpoint.region` from `AWS_REGION` (default `us-east-1`), path-style access, SSL off, `directory.marker.retention=keep`, and the credentials provider `SimpleAWSCredentialsProvider` with **no global key**. Per mounted file: `fs.s3a.bucket.<bucket>.access.key` and `.secret.key`. S3A picks the key by the checkpoint's bucket, so notebooks of several products work in one kernel, and a bucket without a key fails at its first access. The redaction pattern covers these settings.
- **Marker retention `keep`**: S3A's default deletes parent directory markers after each write, up to `checkpoints/` itself, which the key may not delete (logged as `MultiObjectDeleteSupport: AccessDenied: checkpoints/` on every write).
- **Delivery**: which keys a process receives is decided outside the session (Airflow run containers: `airflow-workflows.md`; Jupyter servers and the keys themselves: `lakehouse-product-access.md`).
- **Iceberg sources with delete or overwrite snapshots**: a stream fails on them unless it sets `streaming-skip-delete-snapshots` or `streaming-skip-overwrite-snapshots` (the job's choice: skipped changes are not applied).
- **Atomicity**: Spark falls back from the FileContext to the FileSystem API for `s3ckpt://` (S3A's FileContext binding accepts only `s3a://`), and S3 renames are not atomic, so each checkpoint must have a single writer.

## Rules
- **Names**: compared after PEP 503 normalization (lowercase; runs of `-`, `_`, `.` become `-`).
- **Lock**: the generator header first; then only `name==version` lines, comments and blank lines; no duplicates; never `pyspark`, `py4j`, `pip`, `setuptools`, `wheel`; not empty.
- **Venv check** (`check-venv PYTHON --lock LOCK [--allow-extra]`): Python 3.10; `pip freeze` run with `PYTHONPATH` and `PIP_*` removed (otherwise `/opt/spark/python` lists `pyspark`) equals the lock exactly; with `--allow-extra`, additional packages are allowed and listed, but every locked version must still match. Both image builds fail on any problem.
- **Extras file** (`requirements.txt` at a product repository's root; see `airflow-workflows.md` for its checkout):
  - UTF-8, at most 64 KiB and 200 requirements; every problem reported as `requirements.txt:<line>: <message>`.
  - Accepted: `name`, optional `[extras]`, optional specifiers (`==`, `!=`, `<=`, `>=`, `<`, `>`, `~=`), optional `; marker`, comments.
  - Refused: any line starting with `-` (options such as `-r`, `-e`, `--index-url`, `--hash`); URLs, `@` references, paths (`.`, `/`, `~`) and continuations; `===`; `pyspark`, `py4j`, `pip`, `setuptools`, `wheel`; a name listed twice. A locked package may be listed; the lock decides its version.
- **Resolution and installs**: always `--only-binary=:all:` and `--constraint` the lock, with `--disable-pip-version-check --no-input --no-cache-dir` and `PIP_*` removed (public PyPI only, no credentials).
  - **CI** (`check-extras`): a dry run with `--ignore-installed` for the runtime's platform: CPython 3.10, `cp310`, `manylinux2014_aarch64` and `manylinux_2_17` to `manylinux_2_31` aarch64 (pip accepts only the exact `--platform` tags given). Prints what it would add.
  - **Airflow** (`install-extras FILE --lock LOCK`): into the run container's venv; then the venv check with `--allow-extra`.
  - **Jupyter** (`lakehouse-install-requirements [PATH] [--reset]` → `install-extras ... --target ~/.local/lakehouse/python3.10`): a dry run against the kernel venv (which sees the folder through `lakehouse-user-extras.pth`, appended after site-packages so locked packages win) lists what is missing; changed projects are removed from the folder by their `RECORD` (never outside it); the missing set is installed with `--no-deps`; the folder records the lock's SHA-256 in `.lakehouse-lock.sha256`. Repeated runs add packages. After a lock change the command refuses until `--reset`, which empties only a folder it manages.
  - **No file** (or comments only): nothing to do, exit 0, no network access. A path that exists but isn't a file is a problem.

## Failure behavior
| Situation | Result |
|---|---|
| Lock malformed | the generator writes nothing; builds and checks fail with the line |
| Venv differs from the lock | the image build fails; the parity verifier fails |
| Refused extras line | CI fails listing every line; `install_requirements` fails before pip runs; the Jupyter command changes nothing |
| Conflict with the lock or no suitable wheel | pip's `ResolutionImpossible` or "No matching distribution", exit 1, in all three places |
| PyPI unreachable | CI fails; `install_requirements` retries twice, then the run stops before any workload code |
| Lock changed since a Jupyter install | the command asks for `--reset` |
| Invalid or unsafe checkpoint key file | `create_spark_session` raises, naming the file |
| Checkpoint in a bucket without a mounted key | the stream fails at its first S3 access (no credentials) |
| Checkpoint outside `checkpoints/` or in another bucket | RustFS refuses (403) |
| Key rotated while a session runs | the next checkpoint access fails (403); restart the run or the server |

## Verification and limits
- **Verified 2026-11-11 (Spark S3 checkpoints)**: host suite 583 passed, 3 skipped (`test_spark_session.py`: `ResolvingFileIO`, key files, settings, quiet loggers, Hypothesis P3 one key pair per bucket and no global key, P4 key-file round trip); `scripts/verify/checkpoint-stream.sh` (batch 0 with 28 rows, a second session resumed with 0 rows, `sources/0/offsets/0` under `s3ckpt://`, a bucket without a key refused); user-confirmed in JupyterHub as `joe-developer` (`(0, 28) (1, 0)`, only `NativeCodeLoader` left in the log).
- **Verified 2026-11-10 (Spark session helper)**: host suite 530 passed (`tests/workload_env/test_spark_session.py`: examples, Hypothesis P1 and P2; image contracts for the `.pth`, the copies and the widget versions); both images with the import checks; parity with 56 packages; UAT and Jenkins on the new workload code; the widget extension enabled in JupyterLab.
- **Verified 2026-11-10 (shared requirements)**:
  - host suite 517 passed (`tests/workload_env`: examples, Hypothesis P1 to P5, image and wiring contracts), Airflow image 51 passed, workload repository 51 passed with DuckDB (P6, P7);
  - both images built with their checks and the parity verifier passed;
  - `default-uat-generate_tpch` 13/13 with `duckdb==1.5.6` installed and all eight TPC-H counts correct; a run without `requirements.txt` installed nothing;
  - Jenkins `default_ci` `main` and `uat` with the extras check and the DuckDB tests;
  - user-confirmed in JupyterHub: the kernel on the venv, `git clone`, `lakehouse-install-requirements`, the `generate_tpch` notebook.
- **Limits**:
  - Jupyter extras last one server session: the user volume is mounted at `/home/jovyan/work` only and stopped servers are removed; rerun the command after every server start.
  - Extras come from public PyPI on every run, with no cache; packages need a CPython 3.10 aarch64 wheel for glibc 2.31 or older (for example, `pytpch` 0.2.0 can't be used).
  - Servers started before an image rebuild keep the old image until restarted.
  - The S3A jars add about 280 MB per image (AWS SDK v1 next to Iceberg's SDK v2); Hadoop 3.4's SDK v2 S3A needs a newer Spark.
