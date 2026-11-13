"""The Airflow and token broker images hold only what the platform uses, with fixed releases (airflow-python-packages)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AIRFLOW = (ROOT / "infra/airflow/Dockerfile").read_text(encoding="utf-8")
BROKER = (ROOT / "infra/airflow-token-broker/Dockerfile").read_text(encoding="utf-8")


def _names(path):
    return [line.split("==")[0].strip() for line in (ROOT / path).read_text().splitlines() if line.strip() and not line.startswith("#")]


def test_airflow_is_the_slim_image_with_only_the_providers_the_platform_uses():
    assert re.search(r"^FROM apache/airflow:slim-3\.3\.2-python3\.10@sha256:[0-9a-f]{64}$", AIRFLOW, re.MULTILINE)
    assert _names("infra/airflow/requirements.txt") == [
        "apache-airflow-providers-fab", "apache-airflow-providers-standard", "apache-airflow-providers-git",
        "apache-airflow-providers-docker", "apache-airflow-providers-postgres", "authlib", "pymysql", "httpx2", "graphviz"]
    assert "constraints-3.3.2/constraints-3.10.txt" in AIRFLOW


def test_security_overrides_are_exact_pins_installed_after_the_constraints_and_checked():
    lines = [line for line in (ROOT / "infra/airflow/security-overrides.txt").read_text().splitlines() if line and not line.startswith("#")]
    assert lines and all(re.fullmatch(r"[A-Za-z0-9_.-]+==[0-9][0-9A-Za-z.]*", line) for line in lines)
    assert AIRFLOW.index("-r /requirements.txt") < AIRFLOW.index("-r /security-overrides.txt") < AIRFLOW.index("pip check")
    assert "rm -rf /home/airflow/.local/share/uv/tools/prek" in AIRFLOW


def test_both_images_upgrade_pip_and_setuptools_and_the_broker_is_checked():
    for dockerfile in (AIRFLOW, BROKER):
        assert re.search(r"--upgrade pip==[\d.]+ setuptools==[\d.]+", dockerfile)
    assert "pip check" in BROKER
    pins = dict(line.split("==") for line in (ROOT / "infra/airflow-token-broker/requirements.txt").read_text().split())
    assert {"fastapi", "starlette", "cryptography"} <= set(pins)
