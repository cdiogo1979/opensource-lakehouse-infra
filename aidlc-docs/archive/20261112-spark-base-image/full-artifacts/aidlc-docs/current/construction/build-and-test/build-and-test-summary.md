# Build and Test Summary — Spark Base Image

| Check | Result |
|---|---|
| Host pytest | 654 passed, 3 skipped (official pinned base, root, venv from /usr/bin/python3, JDK copy and JAVA_HOME, lock generator) |
| `workload-python-parity.sh` | OK: 56 packages in both images; one Lakehouse kernel |
| Images | runtime: root, Java 17.0.19 at /opt/java/openjdk, Python 3.10.12, spark-core 3.5.9, Iceberg 1.10.2, S3A, token provider; single-user JAVA_HOME=/opt/java/openjdk |
| Trivy MEDIUM+ (C/H/M) | old base 255/3188/8580 -> new runtime 23/607/1161; single-user 8/136/197 |
| Remaining criticals | linux-libc-dev x16 (kernel headers, no fix); Spark 3.5.9's own jars: netty-handler x3, avro 1.7.7 (hadoop-client-runtime), derby, zookeeper, jackson-mapper-asl; certifi in the venv's pip (workload-lock intent) |
| Live: `lakehouse.sh start` | OK; reconciler started by start (previous intent) |
| Live: `smoke-spark.sh` | prod, UAT, dev smoke tables created, read back, vended credentials |
| Live: `role-matrix.py --product default` | developer, analyst, owner, writer matched; cleanup done |
| Live: `checkpoint-stream.sh` | first run, resume, fail-closed key check, cleanup |
| Live: `start-airflow` + UAT `tpch_medallion` (`live_spark_359`) | success; scheduler image local/lakehouse-spark-runtime:3.5.9_1.10.2; MV deploy unchanged; silver orders merged 15000 |
| Live (user): Jupyter Spark read | "worked fine"; server on the new image (JAVA_HOME /opt/java/openjdk, spark-core 3.5.9) |
