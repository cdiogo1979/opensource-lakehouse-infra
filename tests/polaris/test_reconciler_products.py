"""Contracts for the scheduled reconciler reading the data product files (FR-8, flow E)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_image_ships_the_product_model_and_pinned_pyyaml():
    dockerfile = (ROOT / "infra/polaris/reconciler/Dockerfile").read_text()
    assert "COPY infra/products/data_products.py ./products/data_products.py" in dockerfile
    assert re.search(r"PyYAML==\d+\.\d+\.\d+", dockerfile)
    assert "ENV LAKEHOUSE_DATA_PRODUCTS_DIR=/opt/lakehouse/data-products" in dockerfile
    run = (ROOT / "infra/polaris/reconciler/run.sh").read_text()
    for script in re.findall(r"python (/opt/lakehouse/\S+\.py)", run):
        assert f"./{script.removeprefix('/opt/lakehouse/')}" in dockerfile, script


def test_reconciler_mounts_the_product_files_read_only():
    compose = (ROOT / "compose.core.yml").read_text()
    service = compose[compose.index("  polaris-group-reconciler:"):compose.index("  rustfs:")]
    assert "- ./data-products:/opt/lakehouse/data-products:ro" in service


def test_reconcilers_refuse_invalid_product_files_before_any_change():
    polaris = (ROOT / "infra/polaris/reconcile-keycloak-groups.py").read_text()
    assert polaris.index("data_products.load_all()") < polaris.index("keycloak_login(keycloak")
    starrocks = (ROOT / "infra/starrocks/reconcile-starrocks-users.py").read_text()
    assert starrocks.index("sr.require_products()") < starrocks.index("read_keycloak_memberships(args")


def test_platform_admin_drops_owner_roles_of_products_being_removed():
    # Build and Test finding: Polaris returned 404 assigning a deleted owner role.
    source = (ROOT / "infra/polaris/reconcile-keycloak-groups.py").read_text()
    assert "principal_roles = principal_roles - missing" in source
    assert 'raise ReconcileError("The role-platform-admin group is missing; nothing changed.")' in source


def test_role_matrix_setup_and_cleanup_use_a_role_that_writes_everywhere():
    # Build and Test finding: a writer reduced to read in prod could not clean up.
    source = (ROOT / "infra/spark-bootstrap/verify_role_matrix.py").read_text()
    assert 'for name in ("writer", "owner") if WRITABLE.get(name, frozenset()) >= ENVIRONMENTS' in source
