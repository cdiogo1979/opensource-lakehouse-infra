# Build Instructions — s3-checkpoints

## Prerequisites
- Docker Desktop (arm64), Python 3 on the host with PyYAML, network access to Maven Central for the image build.
- The stack's runtime credentials in `.runtime/` (created by `scripts/setup/prepare-runtime.py`).

## Code analysis
The repository has no CI quality entry point (the root `Jenkinsfile` was retired) and no linter configuration. Read-only checks run on the changed Python files:
`ruff check --line-length 200 <files>`, `flake8 --max-line-length 200 <files>`, `bandit -q <files>`; shell scripts with `bash -n`.

## Build
```sh
docker build -t local/lakehouse-spark-runtime:3.5.5_1.10.2 -f infra/spark-runtime/Dockerfile .   # also part of start and start-airflow
./scripts/lakehouse.sh start            # rebuilds the Jupyter image, recreates the Hub
python3 infra/rustfs/bootstrap-checkpoint-keys.py   # or the product bootstrap scripts
./scripts/lakehouse.sh start-airflow    # recreates Airflow with the key folder mount
```

## Expected result
- `/opt/spark/jars/hadoop-aws-3.3.4.jar` and `aws-java-sdk-bundle-1.12.262.jar` in both images (Maven `--strict-checksums`).
- One key per product environment bucket under `.runtime/credentials/checkpoint-keys/` (600) and `.runtime/container-mounts/checkpoint-keys/` (644), plus `.buckets.json`.

## Troubleshooting
- `Checkpoint keys are not staged for: ...` at `start-airflow`: run the product bootstrap.
- `RustFS policy ... could not be verified after update`: the policy comparison does not match the stored form (fixed for reordered condition values).
