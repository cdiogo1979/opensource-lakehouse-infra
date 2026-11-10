"""Source contracts for the approved JupyterHub identity journey."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load source contract module: {module_name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


POLICY = load_module(
    "unit4_lakehouse_policy", ROOT / "infra/jupyter/hub/lakehouse_policy.py"
)
ROLE_MATRIX = load_module(
    "unit4_role_matrix", ROOT / "infra/spark-bootstrap/verify_role_matrix.py"
)


def test_keycloak_group_claim_and_hub_admission_match_approved_personas():
    realm = json.loads((ROOT / "infra/keycloak/realm-contract.json").read_text())
    approved = {"role-default-developer", "role-default-analyst", "role-platform-admin"}

    assert set(realm["clients"]["jupyterhub"]["group_values"]) == approved
    assert POLICY.APPROVED_GROUPS == approved
    assert POLICY.eligible_group_names(
        ["role-default-developer", "role-default-owner"]
    ) == {"role-default-developer"}
    assert POLICY.eligible_group_names(
        ["role-default-owner", "role-default-writer"]
    ) == set()


def test_browser_oidc_uses_pkce_and_disables_password_authentication():
    realm = json.loads((ROOT / "infra/keycloak/realm-contract.json").read_text())
    hub_config = (ROOT / "infra/jupyter/hub/jupyterhub_config.py").read_text()
    client = realm["clients"]["jupyterhub"]

    assert client["type"] == "confidential OIDC Authorization Code client"
    assert client["pkce"] == "S256"
    assert "c.GenericOAuthenticator.enable_pkce = True" in hub_config
    assert "c.GenericOAuthenticator.basic_auth = False" in hub_config
    assert "c.GenericOAuthenticator.authorize_url" in hub_config


@pytest.mark.parametrize(
    ("role", "readable", "writable"),
    [
        ("developer", {"prod", "uat", "dev"}, {"dev"}),
        ("analyst", {"prod"}, set()),
        ("owner", {"prod", "uat", "dev"}, {"prod", "uat", "dev"}),
        ("writer", {"prod", "uat", "dev"}, {"prod", "uat", "dev"}),
    ],
)
def test_role_journey_contract(role, readable, writable):
    for environment in {"prod", "uat", "dev"}:
        assert ROLE_MATRIX.role_can_access({role}, environment, "read") == (
            environment in readable
        )
        assert ROLE_MATRIX.role_can_access({role}, environment, "write") == (
            environment in writable
        )


def test_unknown_or_malformed_identity_is_denied_by_default():
    assert POLICY.eligible_group_names({"role-default-developer": True}) == set()
    assert not ROLE_MATRIX.role_can_access({"unexpected-role"}, "prod", "read")
    assert not ROLE_MATRIX.role_can_access(
        {"role-default-developer"}, "unknown", "read"
    )
