"""Contracts for the default bootstrap users, platform-admin group, and writer client."""

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
IDENTITIES = json.loads((ROOT / "infra/keycloak/bootstrap-users.json").read_text(encoding="utf-8"))


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


realm = load("bootstrap_realm_users", "infra/keycloak/bootstrap-realm.py")
users = load("bootstrap_users", "infra/keycloak/bootstrap-users.py")


def test_identity_file_is_the_approved_user_and_group_set():
    assert IDENTITIES["default_password"] == "ChangeM3!"
    assert {u["username"]: u["group"] for u in IDENTITIES["users"]} == {
        "joe-developer": "role-default-developer",
        "peter-analyst": "role-default-analyst",
        "maria-owner": "role-default-owner",
        "srv-default-writer": "role-default-writer",
        "platform-admin": "role-platform-admin",
    }
    assert set(IDENTITIES["groups"]) == set(realm.GROUP_PRODUCT_ROLES)
    assert realm.load_bootstrap_identities()["users"] == IDENTITIES["users"]


def test_bootstrap_users_get_a_permanent_password_and_complete_profile():
    user = IDENTITIES["users"][0]
    rep = realm.bootstrap_user_representation(user, "ChangeM3!", "lakehouse.local")
    assert rep["credentials"] == [{"type": "password", "value": "ChangeM3!", "temporary": False}]
    assert rep["requiredActions"] == [] and rep["enabled"] is True and rep["emailVerified"] is True
    assert rep["email"] == "joe-developer@lakehouse.local" and rep["firstName"] and rep["lastName"]


def test_platform_admin_carries_the_owner_product_role():
    assert realm.GROUP_PRODUCT_ROLES["role-platform-admin"] == "role-default-owner"
    for role in realm.ROLES:
        assert realm.GROUP_PRODUCT_ROLES[role] == role


def test_writer_client_uses_the_password_grant_with_a_one_hour_token():
    client = realm.writer_client_configuration("secret")
    assert client["clientId"] == "lakehouse-writer"
    assert client["directAccessGrantsEnabled"] is True
    assert client["serviceAccountsEnabled"] is False and client["standardFlowEnabled"] is False
    assert client["attributes"]["access.token.lifespan"] == "3600"


def test_realm_bootstrap_is_create_only_and_retires_the_old_writer_and_owner_logic():
    source = (ROOT / "infra/keycloak/bootstrap-realm.py").read_text(encoding="utf-8")
    assert "write-service-account" not in source
    assert "platform-admin-password" not in source and "ensure_owner_user" not in source
    assert "service-account-user" not in source

    class ExistingUserAPI:
        def __init__(self):
            self.posts = 0

        def request(self, method, path, payload=None, *, query=None):
            if method == "GET":
                return 200, [{"id": "1", "username": "joe-developer"}]
            self.posts += 1
            return 201, None

    api = ExistingUserAPI()
    assert realm.create_missing_bootstrap_user(api, IDENTITIES["users"][0], "ChangeM3!", "lakehouse.local") is None
    assert api.posts == 0


def test_enforcing_plan_resets_password_and_normalizes_groups():
    assert users.plan_user_changes(False, set(), "role-default-owner") == {
        "create": True, "update_profile": False, "reset_password": False, "remove_groups": set(), "add_group": True}
    plan = users.plan_user_changes(True, {"role-default-owner", "role-default-writer", "custom"}, "role-default-owner")
    assert plan["reset_password"] is True and plan["update_profile"] is True
    assert plan["remove_groups"] == {"role-default-writer", "custom"} and plan["add_group"] is False
    plan = users.plan_user_changes(True, set(), "role-platform-admin")
    assert plan["add_group"] is True and plan["remove_groups"] == set()


def test_enforcement_only_touches_the_listed_users_and_is_wired_into_product_bootstrap():
    source = (ROOT / "infra/keycloak/bootstrap-users.py").read_text(encoding="utf-8")
    assert 'for user in identities["users"]' in source
    product = (ROOT / "scripts/bootstrap-default-product.sh").read_text(encoding="utf-8")
    assert product.index("python3 infra/keycloak/bootstrap-realm.py") < product.index("scripts/bootstrap-users.sh")
    assert product.index("scripts/bootstrap-users.sh") < product.index("reconcile-keycloak-groups.py")


def test_writer_consumers_use_srv_default_writer():
    for relative in ("infra/airflow-token-broker/app.py", "infra/spark-bootstrap/create_smoke_tables.py",
                     "scripts/verify-polaris-keycloak-auth.py", "scripts/verify-keycloak-outage.py",
                     "scripts/verify-polaris-oidc-negative-cases.py"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "write-service-account" not in text, relative
        assert "srv-default-writer" in text, relative
    broker = (ROOT / "infra/airflow-token-broker/app.py").read_text(encoding="utf-8")
    assert '"grant_type": "password"' in broker and 'preferred_username' in broker
    compose = (ROOT / "docker-compose.airflow.yml").read_text(encoding="utf-8")
    assert "KEYCLOAK_WRITER_PASSWORD_FILE: /run/secrets/srv_default_writer_password" in compose
    assert "ChangeM3!" not in compose


def test_polaris_reconciler_maps_platform_admin_to_owner():
    reconciler = load("reconcile_groups", "infra/polaris/reconcile-keycloak-groups.py")
    assert reconciler.GROUP_PRINCIPAL_ROLES["role-platform-admin"] == "role-default-owner"
    assert "role-platform-admin" not in reconciler.GROUPS


def test_platform_admin_group_administers_only_the_lakehouse_realm():
    assert realm.REALM_ADMIN_GROUP == "role-platform-admin" and realm.REALM_ADMIN_ROLE == "realm-admin"
    source = (ROOT / "infra/keycloak/bootstrap-realm.py").read_text(encoding="utf-8")
    assert 'grant_realm_admin(api, groups[REALM_ADMIN_GROUP]["id"])' in source
    assert "/admin/realms/master" not in source.replace('"/realms/master/protocol', "")

    class RealmAPI:
        def __init__(self):
            self.assigned = None

        def request(self, method, path, payload=None, *, query=None):
            if path.endswith("/clients") and method == "GET":
                return 200, [{"id": "rm", "clientId": "realm-management"}]
            if path.endswith("/clients/rm/roles/realm-admin"):
                return 200, {"id": "ra", "name": "realm-admin"}
            if path.endswith("/groups/g1/role-mappings/clients/rm"):
                if method == "GET":
                    return 200, []
                self.assigned = (path.split("/realms/")[1].split("/")[0], payload)
                return 204, None
            raise AssertionError((method, path))

    api = RealmAPI()
    realm.grant_realm_admin(api, "g1")
    assert api.assigned == ("lakehouse", [{"id": "ra", "name": "realm-admin"}])
    contract = json.loads((ROOT / "infra/keycloak/realm-contract.json").read_text(encoding="utf-8"))
    assert contract["platform_admin_group"]["keycloak_client_roles"] == {"realm-management": ["realm-admin"]}
