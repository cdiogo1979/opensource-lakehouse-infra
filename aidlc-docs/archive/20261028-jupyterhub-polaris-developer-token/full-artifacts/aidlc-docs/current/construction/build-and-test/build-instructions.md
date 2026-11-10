# Build Instructions

## Prerequisites

- Docker Engine with BuildKit and Docker Compose V2.
- Python 3 for repository scripts and source-level checks.
- Network access from Docker build stages to the pinned base images and Python package index.
- ARM64 Docker host for the currently pinned Jupyter and Spark base image digests.

## Build

From the repository root:

```bash
docker build -t local/lakehouse-jupyter-singleuser:6.1.1-spark \
  -f infra/jupyter/singleuser/Dockerfile .
docker compose -f docker-compose.yml build jupyterhub
```

Validate Compose and source syntax:

```bash
docker compose -f docker-compose.yml config --quiet
python3 -m compileall -q infra/keycloak/bootstrap-realm.py \
  infra/jupyter/hub/jupyterhub_config.py infra/jupyter/hub/lakehouse_policy.py \
  infra/jupyter/hub/lakehouse_spawner.py scripts/prepare-lakehouse-runtime.py \
  scripts/validate-jupyterhub-credentials.py
bash -n scripts/lakehouse.sh infra/jupyter/singleuser/start-session.sh
python3 -m json.tool infra/keycloak/realm-contract.json
```

The image build resolves and installs the listed Hub dependencies, but `requirements-lock.txt` still contains direct constraints only. The complete transitive lock is a reproducibility prerequisite and remains outstanding. Do not treat the image build as proving a fully locked dependency supply chain.

## Start the local stack

Starting providers mutates local runtime state and is not part of the image-only build. To start the full local flow after confirming the intended local runtime is available:

```bash
scripts/lakehouse.sh start
```

The command prepares protected credentials, builds both images, starts providers, reconciles the Keycloak realm, and starts JupyterHub.
