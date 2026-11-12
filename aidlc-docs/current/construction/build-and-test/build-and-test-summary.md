# Build and Test Summary — 20261112-spark-image-hardening

- Builds: `local/lakehouse-spark-runtime:3.5.9_1.10.2` (206 jars, 194 deb packages; no `linux-libc-dev`, gcc; build checks Python 3.10.12, OpenJDK 17.0.19, Spark 3.5.9) and `local/lakehouse-jupyter-singleuser:6.1.1-spark`.
- Tests: 661 passed, 3 skipped (662 after the PermissionError fix) (new: targets of the scan, every built image scanned, workflow on arm64 with `--build`, no Docker socket, runtime without toolchain and unused jars).
- Parity: `workload-python-parity.sh` OK.
- Spark smoke (`spark-submit`, local): Parquet 5, ORC 5, Iceberg 2 rows; in-memory catalog.
- Live: `checkpoint-stream.sh` passed; `default-uat-test_environment` run succeeded (9 tasks); Jupyter server restarted on the new image and a Spark notebook ran (user).
- Dry-run scan (15 targets): Spark runtime critical 23 -> 5 (Netty x3, Avro 1.7.7, jackson-mapper-asl, Spark-bundled); single-user 6; Airflow as built 23 (follow-up intent).
