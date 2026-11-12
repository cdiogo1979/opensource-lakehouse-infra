# Requirements — Spark Image Hardening and Built-Image Scanning

## Request
"i still dont understand why do i see so many critical issues in the spark runtime image that we just fixed" → "yes" to: (1) scan the images we build, (2) remove the kernel headers, (3) remove unused jars.

## Findings (probes on local/lakehouse-spark-runtime:3.5.9_1.10.2)
- The workflow scans `apache/spark:3.5.9` as published (48 critical) and the never-shipped `maven` build stage; the built image has 23 critical (16 `linux-libc-dev`, 7 jars).
- `linux-libc-dev` is the bottom of the base's compiler toolchain (`build-essential`, gcc/g++, libc6-dev, python3.10-dev, ...). The platform installs only prebuilt wheels (the lock, product extras), so no compiler is needed. `apt-get purge --auto-remove linux-libc-dev` removes 80 packages, among them Perl, X11 and image libraries, `libpython3.10` (embedding library) and `netbase`; none of `python3.10`, `python3.10-venv`, `libc6`, `ca-certificates`, `openssl`.
- Unused jars (Spark runs `local[*]` on Iceberg's REST catalog; no Hive in the configuration): Hive (`hive-*`, `spark-hive*`) and its Derby, ZooKeeper and Curator (standalone-master HA), and the Kubernetes, YARN and Mesos cluster managers.

## Functional requirements
- **FR-1 Scan what runs**: the workflow builds the platform's images on GitHub's arm64 runner (`ubuntu-24.04-arm`) and scans them: `local/lakehouse-spark-runtime`, `-jupyter-singleuser`, `-jupyterhub`, `-airflow`, `-airflow-token-broker`, `-jenkins`, `-ldap`, `-polaris-group-reconciler` (each mapped to its Dockerfile's last `FROM` line); external images that run as pinned stay scanned as today; bases of built images and build-only stages are no longer separate targets (their earlier alerts close through the stale-target step).
- **FR-2 No toolchain in the Spark runtime**: after the build steps, `apt-get purge --auto-remove linux-libc-dev` with `netbase` kept; the image check confirms Python, the venv, Java and Spark still run.
- **FR-3 No unused jars**: remove Hive (`hive-*`, `spark-hive_*`, `spark-hive-thriftserver_*`), `derby-*`, `zookeeper*`, `curator-*`, `spark-kubernetes_*`, `kubernetes-*`, `spark-yarn_*`, `hadoop-yarn-server-web-proxy-*`, `spark-mesos_*`, `mesos-*`; keep everything else (avro, jackson-mapper-asl/core-asl, netty stay: used by Hadoop, Parquet or Spark core). A build check fails if any of the removed jars come back.
- **FR-4 Docs**: vulnerability-alerts (built images scanned), workload-python or Spark notes (no compiler, removed jars: no Hive support, local mode only).

## Non-functional and checks
- **NFR-1** Tests updated; parity OK; Trivy of the built runtime before/after.
- **NFR-2** Live (approval): `start`, smoke-spark, role-matrix, checkpoint-stream, `start-airflow` and a UAT `tpch_medallion` run, a Jupyter Spark session (user).
- **NFR-3** First workflow run: built images scanned, base/maven categories closed; run time recorded.
