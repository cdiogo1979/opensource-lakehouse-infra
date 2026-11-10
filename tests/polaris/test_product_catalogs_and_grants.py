"""Contracts for shared catalogs, product namespaces, and namespace-scoped grants (FR-5, BR-2, BR-7)."""

import importlib.util
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


catalogs = load("polaris_catalogs", "infra/polaris/bootstrap-catalogs.py")
auth = load("polaris_authorization", "infra/polaris/bootstrap-product-authorization.py")
dp = auth.data_products
DEFAULT = dp.load_product(ROOT / "data-products/default.yaml")
SALES = dp.parse_product(yaml.safe_load(dp.render_template("sales")), "sales.yaml")


def test_allowed_locations_start_with_the_catalog_base_and_add_each_product():
    assert catalogs.desired_allowed_locations("prod", DEFAULT, [DEFAULT]) == ["s3://bucket-default/lakehouse/"]
    assert catalogs.desired_allowed_locations("dev", DEFAULT, [DEFAULT, SALES]) == [
        "s3://bucket-default-dev/lakehouse_dev/", "s3://bucket-sales-dev/lakehouse_dev/",
    ]


class FakeCatalogs:
    def __init__(self, allowed):
        self.catalog = {
            "name": "lakehouse", "type": "INTERNAL", "entityVersion": 3,
            "properties": {"default-base-location": "s3://bucket-default/lakehouse/"},
            "storageConfigInfo": {"storageType": "S3", "allowedLocations": allowed, "endpointInternal": catalogs.S3_ENDPOINT,
                                  "pathStyleAccess": True, "region": catalogs.REGION},
        }
        self.namespaces = {}
        self.calls = []

    def call(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if path == "/api/management/v1/catalogs/lakehouse":
            if method == "GET":
                return 200, self.catalog
            self.catalog["storageConfigInfo"] = payload["storageConfigInfo"]
            return 200, self.catalog
        match = re.fullmatch(r"/api/catalog/v1/lakehouse/namespaces(?:/([^/]+))?", path)
        if match and method == "GET":
            name = match.group(1)
            return (200, {"properties": self.namespaces[name]}) if name in self.namespaces else (404, None)
        if match and method == "POST":
            self.namespaces[payload["namespace"][0]] = dict(payload["properties"])
            return 200, None
        raise AssertionError((method, path))


def test_catalog_allowed_locations_converge_and_other_settings_are_checked():
    api = FakeCatalogs(["s3://bucket-default/lakehouse/"])
    allowed = ["s3://bucket-default/lakehouse/", "s3://bucket-sales/lakehouse/"]
    catalogs.ensure_catalog(api, "lakehouse", "s3://bucket-default/lakehouse/", allowed, dry_run=True)
    assert not any(method == "PUT" for method, _, _ in api.calls)
    catalogs.ensure_catalog(api, "lakehouse", "s3://bucket-default/lakehouse/", allowed, dry_run=False)
    update = next(payload for method, _, payload in api.calls if method == "PUT")
    assert update["currentEntityVersion"] == 3 and update["storageConfigInfo"]["allowedLocations"] == allowed
    api.catalog["storageConfigInfo"]["region"] = "eu-west-1"
    try:
        catalogs.ensure_catalog(api, "lakehouse", "s3://bucket-default/lakehouse/", allowed, dry_run=False)
    except catalogs.BootstrapError as error:
        assert "conflicts" in str(error)
    else:
        raise AssertionError("a changed region must be refused")


def test_product_namespace_gets_its_bucket_location_and_default_keeps_the_derived_one():
    api = FakeCatalogs(["s3://bucket-default/lakehouse/"])
    base = "s3://bucket-default/lakehouse/"
    catalogs.ensure_namespace(api, DEFAULT.environment("prod"), base, dry_run=False)
    catalogs.ensure_namespace(api, SALES.environment("prod"), base, dry_run=False)
    assert api.namespaces["default_lh"] == {}
    assert api.namespaces["sales_lh"] == {"location": "s3://bucket-sales/lakehouse/sales_lh/"}
    api.namespaces["sales_lh"] = {"location": "s3://elsewhere/sales_lh/"}
    try:
        catalogs.ensure_namespace(api, SALES.environment("prod"), base, dry_run=False)
    except catalogs.BootstrapError as error:
        assert "another location" in str(error)
    else:
        raise AssertionError("a namespace elsewhere must be refused")


def test_grant_levels_are_namespace_scoped_and_never_manage_namespaces_or_access():
    grants = auth.desired_grants(SALES, "owner", "prod")
    assert ("catalog", "NAMESPACE_LIST") in grants and ("catalog", "CATALOG_READ_PROPERTIES") in grants
    assert {key[0] for key in grants} == {"catalog", "namespace"}
    assert {key[1] for key in grants if key[0] == "namespace"} == {"sales_lh"}
    privileges = {key[-1] for key in grants}
    assert "TABLE_DROP" in privileges
    assert not privileges & {"NAMESPACE_CREATE", "NAMESPACE_DROP", "NAMESPACE_WRITE_PROPERTIES", "CATALOG_MANAGE_CONTENT", "CATALOG_MANAGE_ACCESS"}
    assert auth.desired_grants(SALES, "analyst", "uat") == set()
    developer_dev = {key[-1] for key in auth.desired_grants(SALES, "developer", "dev")}
    assert "TABLE_WRITE_DATA" in developer_dev and "TABLE_DROP" not in developer_dev
    developer_prod = {key[-1] for key in auth.desired_grants(SALES, "developer", "prod")}
    assert "TABLE_READ_DATA" in developer_prod and "TABLE_WRITE_DATA" not in developer_prod


def test_default_migration_plan_adds_namespace_grants_and_revokes_catalog_wide_ones():
    # Today's grants on role-default-developer-lakehouse_dev-catalog (catalog-wide WRITE).
    today = {("catalog", p) for p in (
        "CATALOG_READ_PROPERTIES", "NAMESPACE_LIST", "NAMESPACE_READ_PROPERTIES", "TABLE_LIST", "TABLE_READ_PROPERTIES",
        "TABLE_READ_DATA", "VIEW_LIST", "VIEW_READ_PROPERTIES", "NAMESPACE_CREATE", "TABLE_CREATE",
        "TABLE_WRITE_PROPERTIES", "TABLE_WRITE_DATA")}
    additions, revocations = auth.plan_grants(today, auth.desired_grants(DEFAULT, "developer", "dev"))
    assert all(key[0] == "namespace" and key[1] == "default_lhdev" for key in additions)
    assert set(revocations) == today - {("catalog", "CATALOG_READ_PROPERTIES"), ("catalog", "NAMESPACE_LIST")}
    owner_today = {("catalog", "CATALOG_MANAGE_CONTENT"), ("catalog", "CATALOG_MANAGE_ACCESS")}
    _, owner_revocations = auth.plan_grants(owner_today, auth.desired_grants(DEFAULT, "owner", "prod"))
    assert set(owner_revocations) == owner_today


def test_unknown_grant_types_are_never_revoked():
    _, revocations = auth.plan_grants({None, ("catalog", "TABLE_READ_DATA")}, set())
    assert revocations == [("catalog", "TABLE_READ_DATA")]


class FakePolaris:
    """Principal roles, catalog roles, grants, and bindings, recording write order."""

    def __init__(self, grants=None):
        self.principal = set()
        self.roles = {catalog: set() for catalog in dp.SHARED_CATALOGS.values()}
        self.grants = grants or {}
        self.bindings = set()
        self.writes = []

    def call(self, method, path, payload=None):
        p = path.removeprefix("/api/management/v1")
        if method != "GET":
            self.writes.append((method, p))
        if p == "/principal-roles":
            if method == "GET":
                return 200, {"roles": [{"name": n} for n in self.principal]}
            self.principal.add(payload["principalRole"]["name"])
            return 201, None
        if (m := re.fullmatch(r"/principal-roles/([^/]+)", p)) and method == "DELETE":
            self.principal.discard(m.group(1))
            return 204, None
        if m := re.fullmatch(r"/catalogs/([^/]+)", p):
            return 200, {}
        if m := re.fullmatch(r"/catalogs/([^/]+)/catalog-roles", p):
            if method == "GET":
                return 200, {"roles": [{"name": n} for n in self.roles[m.group(1)]]}
            self.roles[m.group(1)].add(payload["catalogRole"]["name"])
            return 201, None
        if m := re.fullmatch(r"/catalogs/([^/]+)/catalog-roles/([^/]+)/grants", p):
            role = (m.group(1), m.group(2))
            current = self.grants.setdefault(role, set())
            if method == "GET":
                return 200, {"grants": [auth.grant_body(k) for k in current]}
            if method == "PUT":
                current.add(auth.grant_key(payload))
                return 201, None
            current.discard(auth.grant_key(payload["grant"]))
            return 200, None
        if (m := re.fullmatch(r"/catalogs/([^/]+)/catalog-roles/([^/]+)", p)) and method == "DELETE":
            self.roles[m.group(1)].discard(m.group(2))
            return 204, None
        if m := re.fullmatch(r"/principal-roles/([^/]+)/catalog-roles/([^/]+)(?:/([^/]+))?", p):
            if method == "GET":
                return 200, {"roles": [{"name": r} for pr, c, r in self.bindings if pr == m.group(1) and c == m.group(2)]}
            if method == "PUT":
                self.bindings.add((m.group(1), m.group(2), payload["catalogRole"]["name"]))
                return 201, None
            self.bindings.discard((m.group(1), m.group(2), m.group(3)))
            return 204, None
        raise AssertionError((method, path))


def test_apply_adds_everything_before_revoking_and_converges():
    stale = ("lakehouse", "role-default-owner-lakehouse-catalog")
    api = FakePolaris({stale: {("catalog", "CATALOG_MANAGE_CONTENT")}})
    api.roles["lakehouse"].add(stale[1])
    converger = auth.Converger(api, dry_run=False)
    auth.apply_products(converger, [DEFAULT, SALES], roles_only=False)
    lakehouse_writes = [w for w in api.writes if "/catalogs/lakehouse/" in w[1]]
    first_revoke = next(i for i, w in enumerate(lakehouse_writes) if w[0] == "POST" and w[1].endswith("/grants"))
    assert all(not (w[0] == "PUT" and w[1].endswith("/grants")) for w in lakehouse_writes[first_revoke:])
    assert ("catalog", "CATALOG_MANAGE_CONTENT") not in api.grants[stale]
    assert api.grants[("lakehouse", "role-sales-analyst-lakehouse-catalog")] == auth.desired_grants(SALES, "analyst", "prod")
    assert "role-sales-analyst-lakehouse_uat-catalog" not in api.roles["lakehouse_uat"]
    assert ("role-sales-writer", "lakehouse_dev", "role-sales-writer-lakehouse_dev-catalog") in api.bindings
    before = len(api.writes)
    auth.apply_products(auth.Converger(api, dry_run=False), [DEFAULT, SALES], roles_only=False)
    assert len(api.writes) == before, "a second apply must change nothing"


def test_dry_run_writes_nothing_and_remove_deletes_the_product_roles():
    api = FakePolaris()
    auth.apply_products(auth.Converger(api, dry_run=True), [SALES], roles_only=False)
    assert api.writes == []
    auth.apply_products(auth.Converger(api, dry_run=False), [SALES], roles_only=False)
    auth.remove_product(auth.Converger(api, dry_run=False), SALES)
    assert api.principal == set() and all(not roles for roles in api.roles.values()) and api.bindings == set()


def test_oidc_filter_accepts_any_product_group_and_the_namespace_flag_is_on():
    properties = (ROOT / "infra/polaris/oidc.properties").read_text(encoding="utf-8")
    pattern = re.search(r"principal-roles-mapper\.filter=(.+)", properties).group(1)
    for group in ("role-default-owner", "role-sales-writer", "role-sls2-analyst"):
        assert re.fullmatch(pattern, group) and dp.GROUP_PATTERN.fullmatch(group)
    for group in ("role-platform-admin", "role-default-guest", "jenkins-break-glass", "role-a-owner"):
        assert not re.fullmatch(pattern, group)
    assert 'polaris.features."ALLOW_NAMESPACE_CUSTOM_LOCATION"=true' in properties


def test_role_matrix_spec_follows_the_product_file_and_lists_other_products_for_isolation():
    matrix = load("role_matrix_cli", "scripts/verify/role-matrix.py")
    spec = matrix.product_spec(SALES, [DEFAULT, SALES])
    assert spec["product"]["lakehouse_dev"] == ["sales_lhdev", "dev", "bucket-sales-dev"]
    assert spec["readable"]["analyst"] == ["prod"] and spec["writable"]["developer"] == ["dev"]
    assert ["lakehouse", "default_lh", "prod"] in spec["foreign"] and all("sales" not in item[1] for item in spec["foreign"])
    verifier = load("verify_role_matrix_spec", "infra/spark-bootstrap/verify_role_matrix.py")
    foreign = verifier.apply_spec(spec)
    assert verifier.role_can_access({"developer"}, "dev", "write") and not verifier.role_can_access({"analyst"}, "uat", "read")
    assert verifier.expected_table_location("lakehouse", "sales_lh", "t") == "s3://bucket-sales/lakehouse/sales_lh/t"
    assert ("lakehouse_uat", "default_lhuat", "uat") in foreign
