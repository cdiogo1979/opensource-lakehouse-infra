"""Contracts for per-product Keycloak identities and the create-user command (FR-3, FR-9, FR-11)."""

import importlib.util
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "infra/keycloak"), str(ROOT / "infra/products")]

import data_products as dp  # noqa: E402
import keycloak_products as kp  # noqa: E402


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


create_user = load("create_user", "infra/keycloak/create-user.py")


class FakeKeycloak:
    """Just enough of the admin API: groups, Polaris client roles, mappings, users, members."""

    def __init__(self):
        self.groups = {"g-admin": "role-platform-admin"}
        self.roles = {}
        self.mappings = {}
        self.users = {"u-sr": "service-account-srv-starrocks"}
        self.members = {}
        self.calls = []
        self.next_id = 0

    def _id(self, prefix):
        self.next_id += 1
        return f"{prefix}{self.next_id}"

    def request(self, method, path, payload=None, *, query=None):
        self.calls.append((method, path))
        base = "/admin/realms/lakehouse"
        path = path.removeprefix(base)
        if method == "GET" and path == "/groups":
            return 200, [{"id": i, "name": n} for i, n in self.groups.items() if n == query["search"]]
        if method == "POST" and path == "/groups":
            self.groups[self._id("g")] = payload["name"]
            return 201, None
        if method == "GET" and path == "/clients":
            return 200, [{"id": f"c-{query['clientId']}", "clientId": query["clientId"]}]
        if method == "GET" and path == "/clients/c-srv-starrocks/service-account-user":
            return 200, {"id": "u-sr", "username": "service-account-srv-starrocks"}
        match = re.fullmatch(r"/clients/c-polaris/roles(?:/(.+))?", path)
        if match:
            name = match.group(1) and match.group(1).replace("%2D", "-")
            if method == "GET":
                return (200, {"id": f"r-{name}", "name": name}) if name in self.roles else (404, None)
            if method == "POST":
                self.roles[payload["name"]] = True
                return 201, None
            if method == "DELETE":
                self.roles.pop(name, None)
                for mapped in self.mappings.values():
                    mapped.discard(name)
                return 204, None
        match = re.fullmatch(r"/groups/([^/]+)/role-mappings/clients/c-polaris", path)
        if match:
            mapped = self.mappings.setdefault(match.group(1), set())
            if method == "GET":
                return 200, [{"id": f"r-{name}", "name": name} for name in mapped]
            mapped.update(item["name"] for item in payload)
            return 204, None
        match = re.fullmatch(r"/groups/([^/]+)", path)
        if match and method == "DELETE":
            self.groups.pop(match.group(1), None)
            return 204, None
        match = re.fullmatch(r"/groups/([^/]+)/members", path)
        if match:
            return 200, [{"username": self.users[u]} for u, gs in self.members.items() if match.group(1) in gs]
        if method == "GET" and path == "/users":
            return 200, [{"id": i, "username": n} for i, n in self.users.items() if n == query["username"]]
        if method == "POST" and path == "/users":
            self.users[self._id("u")] = payload["username"]
            return 201, None
        match = re.fullmatch(r"/users/([^/]+)/groups(?:/([^/]+))?", path)
        if match:
            if method == "GET":
                return 200, [{"id": g} for g in self.members.get(match.group(1), set())]
            self.members.setdefault(match.group(1), set()).add(match.group(2))
            return 204, None
        match = re.fullmatch(r"/users/([^/]+)", path)
        if match and method == "DELETE":
            self.users.pop(match.group(1), None)
            return 204, None
        raise AssertionError(f"unexpected call {method} {path}")

    def group_id(self, name):
        return next(i for i, n in self.groups.items() if n == name)

    def user_id(self, name):
        return next(i for i, n in self.users.items() if n == name)


@pytest.fixture
def sales(tmp_path, monkeypatch):
    monkeypatch.setattr(kp, "ROOT", tmp_path)
    return dp.parse_product(yaml.safe_load(dp.render_template("sales")), "sales.yaml")


def test_apply_creates_groups_roles_admin_mapping_service_membership_and_writer(sales, tmp_path):
    api = FakeKeycloak()
    changes = kp.apply_product(api, sales, log=lambda _: None)
    assert set(sales.group_names()) <= set(api.groups.values())
    assert set(api.roles) == set(sales.group_names())
    for group in sales.group_names():
        assert api.mappings[api.group_id(group)] == {group}
    assert api.mappings["g-admin"] == {"role-sales-owner"}
    assert api.group_id("role-sales-writer") in api.members["u-sr"]
    writer = api.user_id("srv-sales-writer")
    assert api.members[writer] == {api.group_id("role-sales-writer")}
    password_file = tmp_path / ".runtime/credentials/srv-sales-writer-password"
    assert password_file.read_text() == "ChangeM3!\n" and password_file.stat().st_mode & 0o777 == 0o600
    assert changes > 0
    # A second apply changes nothing and never resets the writer's password file.
    password_file.write_text("rotated\n")
    assert kp.apply_product(api, sales, log=lambda _: None) == 0
    assert password_file.read_text() == "rotated\n"


def test_dry_run_changes_nothing(sales, tmp_path):
    api = FakeKeycloak()
    lines = []
    assert kp.apply_product(api, sales, log=lines.append, dry_run=True) > 0
    assert all(line.startswith("would ") for line in lines)
    assert not any(method in {"POST", "PUT", "DELETE"} for method, _ in api.calls)
    assert not (tmp_path / ".runtime").exists()


def test_bootstrap_writer_is_left_to_the_bootstrap_users(tmp_path, monkeypatch):
    monkeypatch.setattr(kp, "ROOT", tmp_path)
    default = dp.load_product(ROOT / "data-products/default.yaml")
    api = FakeKeycloak()
    kp.apply_product(api, default, log=lambda _: None)
    assert "srv-default-writer" not in api.users.values()
    assert not (tmp_path / ".runtime").exists()


def test_members_exclude_the_starrocks_service_account(sales):
    api = FakeKeycloak()
    kp.apply_product(api, sales, log=lambda _: None)
    members = kp.product_members(api, sales)
    assert members["writer"] == ["srv-sales-writer"] and members["owner"] == []


def test_remove_deletes_everything_and_is_rerunnable(sales, tmp_path):
    api = FakeKeycloak()
    kp.apply_product(api, sales, log=lambda _: None)
    kp.remove_product(api, sales, log=lambda _: None)
    assert set(api.groups.values()) == {"role-platform-admin"}
    assert api.roles == {} and api.mappings["g-admin"] == set()
    assert "srv-sales-writer" not in api.users.values()
    assert not (tmp_path / ".runtime/credentials/srv-sales-writer-password").exists()
    assert kp.remove_product(api, sales, log=lambda _: None) == 0


@pytest.mark.parametrize("username", ["a", "Joe", "srv-sales-writer", "service-account-x", "admin", "jenkins-break-glass", "joe smith"])
def test_create_user_refuses_invalid_or_reserved_usernames(username):
    with pytest.raises(create_user.UserError):
        create_user.validate(username, None, None, None)


def test_create_user_representation_has_no_groups_and_a_permanent_password():
    create_user.validate("anna.lee", "anna@example.com", "Anna", "Lee")
    user = create_user.representation("anna.lee", None, "Anna", None, "ChangeM3!")
    assert user["groups"] == [] and user["enabled"] and user["requiredActions"] == []
    assert user["credentials"] == [{"type": "password", "value": "ChangeM3!", "temporary": False}]
    assert user["email"] == "anna.lee@lakehouse.local" and "lastName" not in user


class AdminAPI:
    """Users joe-developer and platform-admin; only platform-admin is in role-platform-admin."""

    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.posts = []

    def login(self):
        pass

    def request(self, method, path, payload=None, *, query=None):
        users = {"joe-developer": "1", "platform-admin": "2"}
        if method == "GET" and path.endswith("/users"):
            name = query["username"]
            return 200, [{"id": users[name], "username": name}] if name in users else []
        if method == "GET" and path.endswith("/users/2/groups"):
            return 200, [{"name": "role-platform-admin"}]
        if method == "GET" and path.endswith("/users/1/groups"):
            return 200, [{"name": "role-default-developer"}]
        if method == "POST" and path.endswith("/users"):
            self.posts.append(payload)
            return 201, None
        raise AssertionError((method, path))


@pytest.fixture
def admin_password_file(tmp_path):
    secret = tmp_path / "admin"
    secret.write_text("x\n")
    return secret


def test_create_user_refuses_an_existing_user(monkeypatch, capsys, admin_password_file):
    monkeypatch.setattr(create_user.realm, "KeycloakAdmin", AdminAPI)
    assert create_user.main(["joe-developer", "--admin-password-file", str(admin_password_file)]) == 1
    assert "already exists" in capsys.readouterr().err


def test_create_user_signs_in_to_the_lakehouse_realm_as_a_platform_admin(monkeypatch, admin_password_file):
    created = {}

    def factory(*args, **kwargs):
        created["api"] = AdminAPI(*args, **kwargs)
        created["args"] = args
        return created["api"]

    monkeypatch.setattr(create_user.realm, "KeycloakAdmin", factory)
    assert create_user.main(["anna", "--admin-password-file", str(admin_password_file)]) == 0
    assert created["api"].kwargs == {"login_realm": "lakehouse"} and created["args"][1] == "platform-admin"
    assert created["api"].posts[0]["username"] == "anna"


def test_a_non_platform_admin_is_refused_before_any_change(monkeypatch, capsys, admin_password_file):
    apis = []
    monkeypatch.setattr(create_user.realm, "KeycloakAdmin", lambda *a, **k: apis.append(AdminAPI(*a, **k)) or apis[-1])
    assert create_user.main(["anna", "--admin-user", "joe-developer", "--admin-password-file", str(admin_password_file)]) == 1
    assert "not a member of role-platform-admin" in capsys.readouterr().err
    assert apis[0].posts == []


def test_admin_password_sources_file_then_environment_never_an_argument(monkeypatch, admin_password_file):
    import argparse

    # Abbreviations are off, so --admin-password is never read as --admin-password-file.
    parser = argparse.ArgumentParser(allow_abbrev=False)
    kp.add_admin_arguments(parser)
    monkeypatch.setenv(kp.ADMIN_PASSWORD_ENV, "from-env")
    assert kp.admin_password(parser.parse_args(["--admin-password-file", str(admin_password_file)])) == "x"
    assert kp.admin_password(parser.parse_args([])) == "from-env"
    monkeypatch.delenv(kp.ADMIN_PASSWORD_ENV)
    monkeypatch.setattr(kp.sys.stdin, "isatty", lambda: False)
    with pytest.raises(kp.KeycloakProductError, match="No admin password"):
        kp.admin_password(parser.parse_args([]))
    with pytest.raises(SystemExit):
        parser.parse_args(["--admin-password", "x"])
    for script in ("infra/keycloak/create-user.py", "infra/keycloak/product-identity.py"):
        assert "allow_abbrev=False" in (ROOT / script).read_text()


def test_create_user_never_takes_a_password_argument():
    source = (ROOT / "infra/keycloak/create-user.py").read_text(encoding="utf-8")
    assert '"--password"' not in source and "--password-file" in source


def test_a_user_without_admin_rights_gets_a_clear_refusal():
    class Forbidden:
        def request(self, method, path, payload=None, *, query=None):
            return 403, None

    with pytest.raises(kp.KeycloakProductError, match="no admin rights"):
        kp.require_platform_admin(Forbidden(), "joe-developer")
