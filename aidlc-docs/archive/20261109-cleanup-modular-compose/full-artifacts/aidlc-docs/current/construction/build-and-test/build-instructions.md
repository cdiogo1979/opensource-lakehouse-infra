# Build Instructions — Cleanup and Modular Compose

- **Prerequisites**: Docker with Compose V2 (Rancher Desktop, containerd image store), Python 3, and OpenSSL.
- **Build and run**: `./scripts/lakehouse.sh start` builds the local images (Spark runtime, Jupyter single-user, Hub, Jenkins) and starts core plus the enabled modules. `./scripts/bootstrap-default-product.sh` also rebuilds the group reconciler.
- **Reproducible builds**: both entry scripts export `BUILDX_NO_DEFAULT_ATTESTATIONS=1`, so unchanged images keep their ID and running containers are not recreated. They also export `COMPOSE_IGNORE_ORPHANS=true`, because each command passes only the enabled module files.
- **Static checks**:
  - `bash -n` on every script
  - `python3 -m py_compile` on `scripts/` and `infra/spark-bootstrap`
  - `docker compose config -q` for five module combinations (covered by `tests/operations/test_compose_modules_contract.py`)
