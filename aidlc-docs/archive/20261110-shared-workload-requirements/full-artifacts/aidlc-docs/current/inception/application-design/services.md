# Services and Orchestration — Shared Workload Requirements

No new long-running service. The orchestration points are:

1. **Lock maintenance (platform operator)**: edit `requirements.in`, run `scripts/setup/lock-workload-python.sh`, rebuild both images (`./scripts/lakehouse.sh` builds the runtime image, then the Jupyter image from it), run `scripts/verify/workload-python-parity.sh`.
2. **Airflow DAG run**: `create_cluster` → `install_requirements` → `validate_environment` → `submit_<task>`… → `stop_cluster` (`ALL_DONE`) → `verify_workloads_succeeded`. `install_requirements` runs once per run in the run's container, as the container's user (root), into the container's own venv; the container is removed at `stop_cluster`, so nothing outlives the run.
3. **Product CI (Jenkins `<product>_ci`)**: the existing "Validate workflows" stage now also checks `requirements.txt`. It needs PyPI access from Jenkins, which exists today.
4. **Jupyter session**: the user runs `lakehouse-install-requirements` from a terminal or `!` in a cell, then restarts the kernel. The packages persist in the user's home volume.
