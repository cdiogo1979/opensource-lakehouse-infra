# Workload Python environment

Reference: the Python and Spark that workload code runs on. Back to the [README](../../README.md).

Workload code runs on the same Python 3.10 and the same packages everywhere: in each Airflow DAG run's Spark container and in the Jupyter kernel.

- **The platform's packages**: `infra/workload-python/requirements.in` pins the top-level packages (PyYAML, requests, pandas, numpy, pyarrow, ipykernel, jupytext, ipywidgets); `requirements.lock` pins every package, dependencies included. PySpark is not in it: both images use the one in `/opt/spark`. The Spark runtime is the official `apache/spark:3.5.9-scala2.12-java17-python3-ubuntu` image (Ubuntu 22.04, Java 17 at `/opt/java/openjdk`); its system Python packages are not available to workload code.
- **Where it lives**: both `local/lakehouse-spark-runtime` and `local/lakehouse-jupyter-singleuser` hold `/opt/lakehouse/venv` with exactly the lock, and `PYSPARK_PYTHON` points at it. Each image build fails if the venv differs from the lock. The images also hold Hadoop S3A (`hadoop-aws` 3.3.4 and its AWS SDK bundle) for streaming checkpoints. The Spark runtime holds no compiler toolchain (every install is `--only-binary=:all:`) and none of Spark's Hive, Derby, ZooKeeper, Kubernetes, YARN or Mesos jars: Spark runs `local[*]` on Iceberg's REST catalog. Jupyter inherits the same `/opt/spark`.
- **Checks**: `scripts/verify/workload-python-parity.sh` checks that both built images hold the workspace lock and identical packages, and that Jupyter offers only the Lakehouse kernel.

## Changing it

Edit `requirements.in`, run `scripts/setup/lock-workload-python.sh` (it resolves the lock in the Spark runtime's base image, so the Python, architecture and glibc match), rebuild the images with `./scripts/lakehouse.sh start` (or `start-airflow` for the runtime image only), and run `scripts/verify/workload-python-parity.sh`. Never edit the lock by hand.

## A product's extra packages

An optional `requirements.txt` at the product repository's root.
- **Lines**: plain requirements only, such as `duckdb==1.5.6` or `requests[socks]>=2.31,<3`, with comments and environment markers. Refused: options (`-r`, `-e`, `--index-url`, ...), URLs, paths and `name @ url` references, and `pyspark`, `py4j`, `pip`, `setuptools`, `wheel`.
- **Constrained**: the lock is always a constraint, so extras can add packages but never change a locked version; a conflict fails.
- **Wheels only**: every package needs a prebuilt wheel for CPython 3.10 on Linux aarch64 with glibc 2.31 or older (`manylinux_2_17` to `manylinux_2_31`, or `manylinux2014`). For example, `pytpch` 0.2.0 has only an x86_64 wheel for glibc 2.34, so it can't be used.
- **CI**: `lakehouse-validate-workflows` resolves the file against the lock for that platform (it needs PyPI) and lists what it would add.
- **Airflow**: `install_requirements` installs it into the run's own container before `validate_environment`, retrying twice 30 seconds apart; a failure stops the run before any workload code, and the container is cleaned up as usual. Without a `requirements.txt` the task does nothing and needs no network.
- **Jupyter**: `lakehouse-install-requirements` (see [JupyterHub](jupyterhub.md)).

## Spark sessions

`lakehouse_spark.create_spark_session(app_name, catalog)` (`infra/workload-python/python/`, at `/opt/lakehouse/python` in both images, on the venv's path through `lakehouse-platform.pth`) is the platform's only copy of the Polaris catalogs (`lakehouse`, `lakehouse_uat`, `lakehouse_dev`, with `ResolvingFileIO`), the token source, redaction, and the checkpoint settings (see [Streaming checkpoints](streaming-checkpoints.md)).
- **Token source**: an Airflow run's broker settings, or the JupyterHub user's token; anything else is an error, with no fallback.
- **Reuse**: a running session is returned when its default catalog matches; another catalog needs a kernel restart.
- **Repositories** load their own `configs/<env>.yml` and pass its `catalog_name`; `spark-defaults.conf` holds only the Iceberg extensions and redaction.
- **Credential lifetimes**: Airflow runs renew their token for up to 24 hours; Jupyter sessions follow your Keycloak sign-in (at most 10 hours); Polaris storage credentials last one hour per table load, so keep a single write under about 50 minutes ([Known limitations](limitations.md)).
