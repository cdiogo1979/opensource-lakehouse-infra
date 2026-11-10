"""Configuration-as-code contract for Jenkins Keycloak SSO and authorization."""

import importlib.util
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CASC = (ROOT / "infra/jenkins/casc/jenkins.yaml").read_text(encoding="utf-8")
SPEC = importlib.util.spec_from_file_location("render_jenkins", ROOT / "infra/products/render_jenkins.py")
render_jenkins = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_jenkins)
dp = render_jenkins.data_products
REALM = "http://keycloak.localhost:8080/realms/lakehouse"
INTERNAL = "http://keycloak:8080/realms/lakehouse"


def matrix_entries() -> dict[str, list[str]]:
    block = CASC.split("projectMatrix:", 1)[1].split("\nunclassified:", 1)[0]
    entries = {}
    for chunk in block.split("- group:")[1:]:
        name = re.search(r'name: "([^"]+)"', chunk).group(1)
        entries[name] = re.findall(r'- "([A-Za-z]+/[A-Za-z]+)"', chunk)
    return entries


def test_browser_endpoints_use_issuer_host_and_back_channel_uses_service_name():
    assert f'authorizationServerUrl: "{REALM}/protocol/openid-connect/auth"' in CASC
    assert f'endSessionUrl: "{REALM}/protocol/openid-connect/logout"' in CASC
    assert f'tokenServerUrl: "{INTERNAL}/protocol/openid-connect/token"' in CASC
    assert f'jwksServerUrl: "{INTERNAL}/protocol/openid-connect/certs"' in CASC
    assert f'userInfoServerUrl: "{INTERNAL}/protocol/openid-connect/userinfo"' in CASC
    assert f'issuer: "{REALM}"' in CASC


def test_client_claims_pkce_and_logout():
    assert 'clientId: "jenkins"' in CASC
    assert 'groupsFieldName: "groups"' in CASC
    assert 'userNameField: "preferred_username"' in CASC
    assert '- "pkce"' in CASC
    assert "logoutFromOpenidProvider: true" in CASC
    assert "rootURLFromRequest: true" in CASC
    assert 'postLogoutRedirectUrl: "http://127.0.0.1:${JENKINS_HOST_PORT}/"' in CASC


def test_secrets_are_read_from_mounted_files_only():
    assert 'clientSecret: "${trim:${readFile:/run/secrets/jenkins_oidc_client_secret}}"' in CASC
    assert 'secret: "${trim:${readFile:/run/secrets/jenkins_break_glass_password}}"' in CASC
    for line in CASC.splitlines():
        if re.search(r"(?i)(secret|password):", line):
            assert "${trim:${readFile:/run/secrets/" in line, line


def test_escape_hatch_is_a_dedicated_admin_group():
    hatch = CASC.split("- escapeHatch:", 1)[1].split("authorizationStrategy:", 1)[0]
    assert 'username: "jenkins-break-glass"' in hatch
    assert 'group: "jenkins-break-glass"' in hatch


def rendered_entries(products) -> dict[str, list[str]]:
    document = yaml.safe_load(render_jenkins.render(CASC, products))
    entries = document["jenkins"]["authorizationStrategy"]["projectMatrix"]["entries"]
    return {entry["group"]["name"]: entry["group"]["permissions"] for entry in entries}


def test_template_uses_the_project_based_matrix():
    assert "globalMatrix" not in CASC and "    projectMatrix:\n" in CASC


def test_template_holds_only_the_static_entries():
    assert matrix_entries() == {
        "role-platform-admin": ["Overall/Administer"],
        "jenkins-break-glass": ["Overall/Administer"],
    }


def test_rendered_global_matrix_for_default_grants_products_only_read():
    default = dp.load_product(ROOT / "data-products/default.yaml")
    assert rendered_entries([default]) == {
        "role-platform-admin": ["Overall/Administer"],
        "jenkins-break-glass": ["Overall/Administer"],
        "role-default-owner": ["Overall/Read"],
        "role-default-developer": ["Overall/Read"],
        "role-default-analyst": ["Overall/Read"],
    }
    block = render_jenkins.render(CASC, [default]).split("projectMatrix:", 1)[1].split("\njobs:", 1)[0]
    for forbidden in ("anonymous", "authenticated", "role-default-writer", "- user:"):
        assert forbidden not in block


def test_rendering_adds_new_products_deterministically_and_keeps_secrets_as_file_reads(tmp_path):
    default = dp.load_product(ROOT / "data-products/default.yaml")
    sales = dp.parse_product(yaml.safe_load(dp.render_template("sales")), "sales.yaml")
    entries = rendered_entries([default, sales])
    assert entries["role-sales-owner"] == ["Overall/Read"] and "role-sales-writer" not in entries
    first, second = render_jenkins.render(CASC, [default, sales]), render_jenkins.render(CASC, [default, sales])
    assert first == second
    assert "${trim:${readFile:/run/secrets/jenkins_oidc_client_secret}}" in first
    output = tmp_path / "jenkins-casc.yaml"
    assert render_jenkins.write_if_changed(output, first) is True
    assert render_jenkins.write_if_changed(output, second) is False


def test_core_settings_preserve_the_migrated_instance():
    assert "numExecutors: 2" in CASC
    assert "mode: NORMAL" in CASC
    assert "crumbIssuer: standard" in CASC
    assert 'url: "http://127.0.0.1:${JENKINS_HOST_PORT}/"' in CASC
    assert "jobs:" not in CASC
