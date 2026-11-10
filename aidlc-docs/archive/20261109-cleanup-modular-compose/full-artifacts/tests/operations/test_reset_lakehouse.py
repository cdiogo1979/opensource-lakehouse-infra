"""Contracts for the full environment reset."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("reset_lakehouse", ROOT / "scripts/operations/reset-lakehouse.py")
reset = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reset)


def test_inventory_selects_only_v2_resources(tmp_path):
    runtime = tmp_path / ".runtime"
    for name in ("credentials", "container-mounts", "airflow-dag-bundles", "aidlc-test-venv"):
        (runtime / name).mkdir(parents=True)
    containers = [
        {"name": "lakehouse-local-keycloak-1", "labels": {"com.docker.compose.project": "lakehouse-local"}},
        {"name": "jupyter-abc", "labels": {"lakehouse-local.role": "jupyter-user-server"}},
        {"name": "spark-run-1", "labels": {"lakehouse-local.role": "airflow-spark-run"}},
        {"name": "hive-dremio-rustfs-jenkins-1", "labels": {"com.docker.compose.project": "hive-dremio-rustfs"}},
        {"name": "k8s_coredns", "labels": {}},
    ]
    volumes = ["lakehouse-local_keycloak-db-data", "lakehouse-local_airflow-postgres-data", "lakehouse-jupyter-home-123",
               "iceberg-poc-jupyterhub-data", "jenkins_home", "lakehouse-local_unknown", "jupyter-platform_jupyterhub-data"]
    networks = ["lakehouse-local_core", "lakehouse-local_rustfs-identity", "bridge", "iceberg-poc-net"]
    inventory = reset.select_inventory(containers, volumes, networks, runtime)
    assert inventory["containers"] == ["jupyter-abc", "lakehouse-local-keycloak-1", "spark-run-1"]
    assert inventory["volumes"] == ["lakehouse-jupyter-home-123", "lakehouse-local_airflow-postgres-data", "lakehouse-local_keycloak-db-data"]
    assert inventory["networks"] == ["lakehouse-local_core", "lakehouse-local_rustfs-identity"]
    assert [Path(p).name for p in inventory["directories"]] == ["airflow-dag-bundles", "container-mounts", "credentials"]


def test_the_full_volume_and_network_lists_cover_every_v2_store():
    assert set(reset.VOLUMES) == {f"lakehouse-local_{n}" for n in (
        "keycloak-db-data", "polaris-db-data", "rustfs-data", "jupyterhub-state", "jenkins-home", "airflow-postgres-data",
        "starrocks-fe-meta", "starrocks-be-storage")}
    assert set(reset.NETWORKS) == {f"lakehouse-local_{n}" for n in (
        "core", "jupyter-user", "data-access", "rustfs-identity", "airflow-internal", "airflow-spark", "starrocks")}


def test_directory_guard_refuses_anything_but_the_generated_runtime_directories(tmp_path):
    runtime = tmp_path / ".runtime"
    (runtime / "credentials").mkdir(parents=True)
    (runtime / "aidlc-test-venv").mkdir()
    outside = tmp_path / "elsewhere" / "credentials"
    outside.mkdir(parents=True)
    link = runtime / "container-mounts"
    link.symlink_to(outside)
    assert reset.is_removable_directory(runtime / "credentials", runtime)
    assert not reset.is_removable_directory(runtime / "aidlc-test-venv", runtime)
    assert not reset.is_removable_directory(outside, runtime)
    assert not reset.is_removable_directory(link, runtime)
    assert not reset.is_removable_directory(runtime, runtime)


def test_confirmation_requires_the_exact_word(monkeypatch):
    monkeypatch.setattr(reset.sys.stdin, "isatty", lambda: True, raising=False)
    for answer, expected in (("reset", True), (" reset ", True), ("yes", False), ("RESET", False), ("", False)):
        monkeypatch.setattr("builtins.input", lambda _prompt, a=answer: a)
        assert reset.confirmed(False) is expected
    assert reset.confirmed(True) is True


def test_non_interactive_runs_need_yes(monkeypatch):
    monkeypatch.setattr(reset.sys.stdin, "isatty", lambda: False, raising=False)
    assert reset.confirmed(False) is False


def test_flags_are_mutually_exclusive_and_wired():
    source = (ROOT / "scripts/operations/reset-lakehouse.py").read_text(encoding="utf-8")
    assert "add_mutually_exclusive_group" in source and '"--yes"' in source and '"--dry-run"' in source
    lakehouse = (ROOT / "scripts/lakehouse.sh").read_text(encoding="utf-8")
    assert 'reset) require_tools; python3 scripts/operations/reset-lakehouse.py "${@:2}" ;;' in lakehouse
    assert "opensource-lakehouse" not in source and "rmi" not in source
