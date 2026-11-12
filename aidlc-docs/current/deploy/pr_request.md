# PR request — Harden the Spark runtime and scan the images as built

## Problem
The vulnerability workflow scanned the upstream bases of the images built here (`apache/spark` 3.5.9 as published: 48 critical) and their build-only stages, not the images that run, so alerts didn't match the platform. The Spark runtime itself still carried the base's compiler toolchain and kernel headers (16 critical in `linux-libc-dev`) and Spark modules the platform never uses (Hive, Derby, ZooKeeper, Kubernetes, YARN, Mesos).

## Solution
- Spark runtime: purge the toolchain (`linux-libc-dev` with `--auto-remove`, keeping `netbase`) and remove `/opt/spark/yarn` and the unused jars (`hive-storage-api` stays: ORC needs it). The build fails if the toolchain returns and checks that Python, Java and `spark-submit` run. Every install is `--only-binary=:all:`, so nothing needs a compiler.
- `scripts/verify/list-images.py --targets`: the Compose files' external images plus the eight images built here, from the Compose `build:` blocks and the `docker build` lines of `scripts/lakehouse.sh`; each points at its Dockerfile's last `FROM` line.
- `scripts/verify/vulnerability-scan.py --build` builds them and scans a `docker save` export (`trivy --input`, no Docker socket); the workflow runs on `ubuntu-24.04-arm` with a 120-minute timeout. Base and build-stage categories close through the stale-target step.
- Docs: vulnerability alerts, workload Python, future work (Spark on Kubernetes would need its jars back).

## Verification
663 tests passed, 3 skipped; parity OK; a Spark job reads and writes Parquet, ORC and Iceberg; live: checkpoint streaming (Polaris, RustFS, token provider) and the `default-uat-test_environment` DAG run succeeded. Dry-run scan: Spark runtime critical 23 -> 5 (Spark-bundled Netty, Avro 1.7.7, jackson-mapper-asl).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
