"""Contracts for the data product and user operator scripts (FR-2, FR-9, FR-11, BR-8, BR-10)."""

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ["create-data-product.sh", "remove-data-product.sh", "create-user.sh", "lib/data-products.sh"]
CLI = ROOT / "infra/products/product-cli.py"


def run(args, env=None, stdin=subprocess.DEVNULL):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, env={**os.environ, **(env or {})}, stdin=stdin)


@pytest.mark.parametrize("script", SCRIPTS)
def test_scripts_parse_under_macos_bash_3_2(script):
    assert run(["/bin/bash", "-n", str(ROOT / "scripts/operations" / script)]).returncode == 0


def test_usage_errors_exit_2():
    assert run(["scripts/operations/create-data-product.sh"]).returncode == 2
    assert run(["scripts/operations/create-data-product.sh", "--init"]).returncode == 2
    assert run(["scripts/operations/remove-data-product.sh"]).returncode == 2
    assert run(["scripts/operations/remove-data-product.sh", "sales", "--bogus"]).returncode == 2


def test_removing_default_or_an_unknown_product_is_refused_before_any_change():
    result = run(["scripts/operations/remove-data-product.sh", "default", "--yes"])
    assert result.returncode == 2 and "cannot be removed" in result.stderr
    result = run(["scripts/operations/remove-data-product.sh", "nosuchproduct", "--yes"])
    assert result.returncode == 2 and "Unknown data product" in result.stderr
    assert not (ROOT / ".runtime/state/data-products/.lock").exists()


def test_without_a_terminal_or_password_the_scripts_refuse(tmp_path):
    env = {"LAKEHOUSE_ADMIN_PASSWORD": "", "LAKEHOUSE_DATA_PRODUCTS_DIR": str(ROOT / "data-products")}
    result = run(["scripts/operations/create-data-product.sh", "data-products/default.yaml", "--dry-run"], env)
    assert result.returncode == 2 and "no admin password" in result.stderr
    assert not (ROOT / ".runtime/state/data-products/.lock").exists(), "the lock must be released on exit"


def test_passwords_never_travel_as_arguments():
    for script in SCRIPTS:
        text = (ROOT / "scripts/operations" / script).read_text()
        assert "--admin-password " not in text and "--password " not in text
    lib = (ROOT / "scripts/operations/lib/data-products.sh").read_text()
    assert "read -r -s password" in lib and 'export LAKEHOUSE_ADMIN_PASSWORD="$password"' in lib


def test_removal_order_matches_the_design():
    text = (ROOT / "scripts/operations/remove-data-product.sh").read_text()
    order = [
        "product-cli.py resolve", "summarize", "Type the product name", "product-cli.py backup",
        "apply_jenkins", "bootstrap-starrocks.py --remove", "bootstrap-product-authorization.py --remove",
        "bootstrap-catalogs.py --remove", "bootstrap-checkpoint-keys.py --remove", "bootstrap-buckets.py --remove", "bootstrap-policies.py --remove",
        "product-identity.py --remove", "reconcile-keycloak-groups.py", "product-cli.py forget",
    ]
    positions = [text.index(marker) for marker in order]
    assert positions == sorted(positions)


def test_apply_order_matches_the_design():
    text = (ROOT / "scripts/operations/create-data-product.sh").read_text()
    order = [
        "product-cli.py validate", "product-identity.py", "bootstrap-buckets.py", "bootstrap-policies.py",
        "bootstrap-checkpoint-keys.py", "bootstrap-catalogs.py", "bootstrap-product-authorization.py", "reconcile-keycloak-groups.py",
        "bootstrap-starrocks.py", "reconcile-starrocks-users.py", "apply_jenkins", "product-cli.py record",
    ]
    positions = [text.index(marker) for marker in order]
    assert positions == sorted(positions)


@pytest.fixture
def products(tmp_path):
    directory = tmp_path / "data-products"
    directory.mkdir()
    (directory / "default.yaml").write_text((ROOT / "data-products/default.yaml").read_text())
    return directory


def cli(products_dir, *args):
    return run(["python3", str(CLI), *args], {"LAKEHOUSE_DATA_PRODUCTS_DIR": str(products_dir)})


def test_init_writes_a_valid_file_and_refuses_existing_or_colliding_names(products):
    result = cli(products, "init", "sales")
    assert result.returncode == 0 and (products / "sales.yaml").exists()
    assert cli(products, "init", "sales").returncode == 2
    assert cli(products, "init", "lakehouse").returncode == 2
    assert cli(products, "validate", str(products / "sales.yaml")).returncode == 0


def test_validate_refuses_a_file_outside_the_products_directory(products, tmp_path):
    outside = tmp_path / "sales.yaml"
    outside.write_text((ROOT / "infra/products/template.yaml").read_text().replace("{name}", "sales"))
    result = cli(products, "validate", str(outside))
    assert result.returncode == 2 and "must live in" in result.stderr


def test_summarize_reports_data_and_members(products, tmp_path):
    members = tmp_path / "members.json"
    members.write_text(json.dumps({"owner": ["anna"], "writer": ["srv-sales-writer"]}))
    empty_tables = tmp_path / "polaris.json"
    empty_tables.write_text(json.dumps({env: {"tables": 0, "views": 0} for env in ("prod", "uat", "dev")}))
    no_objects = tmp_path / "storage.json"
    no_objects.write_text(json.dumps({"prod": 0, "uat": 0, "dev": 0}))
    result = cli(products, "summarize", "sales", str(members), str(empty_tables), str(no_objects))
    assert result.returncode == 0 and "anna, srv-sales-writer" in result.stdout
    no_objects.write_text(json.dumps({"prod": 4, "uat": 0, "dev": 0}))
    assert cli(products, "summarize", "sales", str(members), str(empty_tables), str(no_objects)).returncode == 10


def test_forget_refuses_default(products):
    assert cli(products, "forget", "default").returncode == 2
    assert (products / "default.yaml").exists()


def test_create_user_script_delegates_to_the_validated_command():
    text = (ROOT / "scripts/operations/create-user.sh").read_text()
    assert re.search(r'exec python3 infra/keycloak/create-user.py "\$@"', text)


def test_checkpoint_keys_follow_the_policies_in_every_bootstrap_and_the_launcher_checks_them():
    default = (ROOT / "scripts/bootstrap-default-product.sh").read_text()
    assert default.index("bootstrap-policies.py") < default.index("bootstrap-checkpoint-keys.py") < default.index("bootstrap-catalogs.py")
    launcher = (ROOT / "scripts/lakehouse.sh").read_text()
    assert "bootstrap-checkpoint-keys.py --check-staged" in launcher
    assert 'rotate-checkpoint-keys) require_tools; python3 infra/rustfs/bootstrap-checkpoint-keys.py --rotate "${@:2}" ;;' in launcher
    start_airflow = launcher[launcher.index("start_airflow() {"):]
    assert start_airflow.index("prepare_checkpoint_keys") < start_airflow.index('"${AIRFLOW_COMPOSE[@]}" up')
