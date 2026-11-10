# Unit 1 Build Instructions — Spark Writer Runtime

## Prerequisites

- Docker Engine with Compose v2 and the `iceberg_net` stack dependencies already available.
- Existing provisioned writer keytab and RustFS writer credentials under `.runtime/credentials/`.
- Do not print or copy credential contents into command output or test artifacts.

## Build and static configuration checks

```bash
docker compose config -q
bash -n infra/spark/entrypoint.sh scripts/start.sh scripts/run-tpch-workload.sh infra/tpch-loader/run-workload.sh
docker compose build spark
```

The derived image retains the pinned upstream Spark 3.5.5/Iceberg 1.8.1 digest and installs Debian `krb5-user`. The upstream image's Bullseye source list contains a pinned Debian snapshot reference; the Dockerfile uses that immutable snapshot because Bullseye's moving security mirror returned 404s for package versions still advertised by its index.

The first image build against the moving mirror failed on stale security package URLs. After switching to the snapshot already documented in the upstream image, the image built successfully.

## Full service startup

The normal operator sequence is documented in `README.md`. Do not recreate an existing Spark service as part of a smoke test when it could interrupt notebooks or current work. Build and Test used an isolated `docker compose run` container for the prior smoke test. The full supervised Spark service still requires a separately scheduled check after confirming service interruption is acceptable.
