"""Airflow follows the data products: staging, the recorded fingerprint, and the operator scripts (FR-3, BR-2)."""

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAKEHOUSE = (ROOT / "scripts/lakehouse.sh").read_text(encoding="utf-8")
LIBRARY = (ROOT / "scripts/operations/lib/data-products.sh").read_text(encoding="utf-8")
CREATE = (ROOT / "scripts/operations/create-data-product.sh").read_text(encoding="utf-8")
REMOVE = (ROOT / "scripts/operations/remove-data-product.sh").read_text(encoding="utf-8")
STAGE = ROOT / "scripts/setup/stage-airflow-writers.py"


def run(*args):
    return subprocess.run([sys.executable, str(STAGE), *args], capture_output=True, text=True, check=False)


def test_previews_list_bundles_and_honour_exclusions():
    assert run("--list").stdout.split() == ["default-main", "default-uat"]
    assert run("--list", "--exclude", "default").stdout.split() == []
    first, second = run("--fingerprint"), run("--fingerprint")
    assert first.returncode == 0 and first.stdout == second.stdout and len(first.stdout.strip()) == 64
    assert run("--fingerprint", "--exclude", "default").stdout != first.stdout
    assert run("--exclude", "default").returncode == 2  # staging never leaves a product out


def test_fingerprint_state_round_trips(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("airflow_bundle_state", ROOT / "scripts/setup/airflow-bundle-state.py")
    state = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(state)
    monkeypatch.setattr(state, "STATE", tmp_path / "airflow-bundles.json")
    assert state.main(["record", "a" * 64]) == 0
    assert state.main(["record", "not-a-fingerprint"]) == 2
    assert '"' + "a" * 64 + '"' in (tmp_path / "airflow-bundles.json").read_text()


def test_start_airflow_stages_first_recreates_the_broker_on_change_and_records_last():
    body = LAKEHOUSE[LAKEHOUSE.index("start_airflow() {"):]
    assert body.index("stage-airflow-writers.py") < body.index("validate-bundle-config.py --host-paths") < body.index("up --build -d")
    assert body.index('if [[ "$fingerprint" != "$recorded" ]]') < body.index("--force-recreate airflow-token-broker")
    assert body.index("scripts/verify/airflow-dags.sh") < body.index('airflow-bundle-state.py record "$fingerprint"')
    assert all("--remove-orphans" not in line for line in LAKEHOUSE.splitlines() if not line.lstrip().startswith("#"))


def test_operators_apply_airflow_only_when_the_fingerprint_changed():
    body = LIBRARY[LIBRARY.index("apply_airflow() {"):LIBRARY.index("jenkins_running() {")]
    order = ['[[ "$current" == "$recorded" ]]', "! airflow_running", '"$dry_run" == true', '"$no_restart" == true', "bash scripts/lakehouse.sh start-airflow"]
    assert [body.index(item) for item in order] == sorted(body.index(item) for item in order)
    assert CREATE.index("product-cli.py record") < CREATE.rindex('apply_airflow false "$no_restart"')
    assert 'apply_airflow true "$no_restart"' in CREATE
    assert REMOVE.index('product-cli.py forget "$name"') < REMOVE.index('apply_airflow false "$no_restart"')
    assert 'apply_airflow true "$no_restart" --exclude "$name"' in REMOVE


def test_dag_verification_expects_every_product_bundle():
    script = (ROOT / "scripts/verify/airflow-dags.sh").read_text(encoding="utf-8")
    assert "stage-airflow-writers.py --list" in script and "lakehouse-main" not in script
