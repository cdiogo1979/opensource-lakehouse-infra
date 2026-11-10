"""Airflow Bundles live inside this repository; the workload repository is not referenced locally."""

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FILES = ("scripts/lakehouse.sh", "scripts/setup/provision-airflow-secrets.sh",
         "infra/airflow/validate-bundle-config.py", "compose.airflow.yml")


def test_no_local_reference_to_the_workload_repository():
    for relative in FILES:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "LAKEHOUSE_PROJECT_ROOT" not in text, relative
        assert "../opensource-lakehouse" not in text, relative


def test_default_bundle_root_is_inside_this_repository():
    assert 'LAKEHOUSE_BUNDLE_HOST_ROOT="${LAKEHOUSE_BUNDLE_HOST_ROOT:-${ROOT_DIR}/.runtime/airflow-dag-bundles}"' in \
        (ROOT / "scripts/lakehouse.sh").read_text(encoding="utf-8")


def run_validator(bundle_root: str, *flags: str):
    config = subprocess.run([sys.executable, str(ROOT / "scripts/setup/airflow-bundle-config.py")],
                            capture_output=True, text=True, check=True).stdout
    env = {**os.environ, "LAKEHOUSE_BUNDLE_HOST_ROOT": bundle_root,
           "LAKEHOUSE_BUNDLE_CONTAINER_ROOT": "/opt/airflow/dag_bundles", "LAKEHOUSE_BUNDLE_CONFIG_LIST": config}
    env.pop("LAKEHOUSE_PROJECT_ROOT", None)
    return subprocess.run([sys.executable, str(ROOT / "infra/airflow/validate-bundle-config.py"), *flags],
                          capture_output=True, text=True, env=env)


def test_host_validation_accepts_only_this_repositorys_bundle_root():
    assert run_validator(str(ROOT / ".runtime/airflow-dag-bundles"), "--host-paths").returncode == 0
    assert run_validator(str(ROOT.parent / "opensource-lakehouse/.runtime/airflow-dag-bundles"), "--host-paths").returncode != 0


def test_container_validation_does_not_need_the_host_repository_path():
    # airflow-init runs the copy baked into the image, where the repository path does not exist.
    assert run_validator("/some/host/path/.runtime/airflow-dag-bundles").returncode == 0
    entrypoint = (ROOT / "infra/airflow/airflow-entrypoint.sh").read_text(encoding="utf-8")
    assert "validate-bundle-config.py" in entrypoint and "--host-paths" not in entrypoint
    assert "validate-bundle-config.py --host-paths" in (ROOT / "scripts/lakehouse.sh").read_text(encoding="utf-8")
