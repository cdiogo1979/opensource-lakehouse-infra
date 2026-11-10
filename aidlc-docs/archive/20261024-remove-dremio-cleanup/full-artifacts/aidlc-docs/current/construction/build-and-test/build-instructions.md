# Build Instructions

## Environment

- Docker Engine and Docker Compose v2.
- The repository's ignored `.runtime/credentials/` files must already exist before starting containers. Do not display or commit them.
- Allow sufficient Docker disk space for Hive, Kerberos, Spark, JupyterHub, and optional workload images.
- The build does not start containers or change Hive, RustFS, KDC, or notebook data.

## Build all configured images

From the project root:

```bash
docker compose --profile workload --profile identity-provisioning --profile jupyter-build build
```

This includes the default services, the TPCH generator and loader, the identity provisioner, and the Jupyter single-user image. Images backed only by pinned upstream images are pulled separately by the startup workflow.

## Configuration and source syntax checks

```bash
docker compose config --quiet
bash -n scripts/bootstrap-local.sh scripts/provision-identities.sh scripts/start.sh scripts/stop.sh scripts/clean.sh scripts/run-tpch-workload.sh infra/spark/entrypoint.sh infra/tpch-loader/run-workload.sh infra/tpch-generator/generate.sh infra/kerberos/entrypoint.sh infra/kerberos/healthcheck.sh infra/identity-provisioner/provision-kerberos-identities.sh infra/identity-provisioner/provision-postgres-roles.sh infra/hive/schema-init.sh
python3 -c 'import ast; from pathlib import Path; paths=list(Path("scripts").glob("*.py"))+list(Path("infra").rglob("*.py")); [(ast.parse(p.read_text(), filename=str(p))) for p in paths]; print(f"Python syntax OK: {len(paths)} files")'
```

These checks are read-only. Confirm the new source paths in Compose resolve to `infra/spark/spark-defaults.conf`, `infra/tpch-loader/load_tpch.py`, and `infra/tpch-generator/`.

## Build result for this run

The command above completed successfully. Built images included Hive Metastore/schema initialization, KDC, identity provisioner, bucket initializer, TPCH generator/loader, JupyterHub, and the Jupyter single-user image. No container was started or stopped.
