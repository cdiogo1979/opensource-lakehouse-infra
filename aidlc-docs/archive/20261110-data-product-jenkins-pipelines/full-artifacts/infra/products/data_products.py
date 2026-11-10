"""Data product model: load, validate, and template the product files.

Every product, ``default`` included, is one YAML file in ``data-products``
holding its whole configuration. The component bootstraps, the reconcilers, and
the app sign-in hooks all read the files through this module, so no component
hard-codes a product. The module depends only on the standard library and PyYAML
so the reconciler, JupyterHub, and Airflow images can copy it as a single file.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import ipaddress
import json
import os
import re
import tempfile
import time
import urllib.parse
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterator

import yaml

ROOT = Path(__file__).resolve().parents[2]
# Containers mount the product files elsewhere; LAKEHOUSE_DATA_PRODUCTS_DIR points there.
PRODUCTS_DIR = Path(os.environ.get("LAKEHOUSE_DATA_PRODUCTS_DIR") or ROOT / "data-products")
STATE_DIR = ROOT / ".runtime" / "state" / "data-products"
TEMPLATE_FILE = Path(__file__).resolve().with_name("template.yaml")

API_VERSION = "lakehouse.local/v1"
DEFAULT_PRODUCT = "default"
ENVIRONMENTS = ("prod", "uat", "dev")
SHARED_CATALOGS = {"prod": "lakehouse", "uat": "lakehouse_uat", "dev": "lakehouse_dev"}
ROLES = ("owner", "developer", "analyst", "writer")
DATA_LEVELS = ("none", "read", "write", "manage")
MV_LEVELS = ("none", "read", "author", "manage")
AIRFLOW_ROLES = ("Admin", "User", "Viewer")
# Jenkins rights apply to the product's folder. The owner is always its admin
# (every folder permission); apps.jenkins lists the other roles. Product groups
# get only Overall/Read globally, so they see Jenkins but no other product.
FOLDER_ADMIN_PERMISSIONS = (
    "Credentials/Create",
    "Credentials/Delete",
    "Credentials/ManageDomains",
    "Credentials/Update",
    "Credentials/View",
    "Job/Build",
    "Job/Cancel",
    "Job/Configure",
    "Job/Create",
    "Job/Delete",
    "Job/Discover",
    "Job/Move",
    "Job/Read",
    "Job/Workspace",
    "Run/Delete",
    "Run/Replay",
    "Run/Update",
    "SCM/Tag",
    "View/Configure",
    "View/Create",
    "View/Delete",
    "View/Read",
)
JENKINS_PERMISSIONS = FOLDER_ADMIN_PERMISSIONS
JENKINS_ROLES = ("developer", "analyst", "writer")
PLATFORM_ADMIN_GROUP = "role-platform-admin"
RESERVED_NAMES = frozenset({"lakehouse", "platform", "admin", "srv", "starrocks", "polaris"})

NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]{1,19}$")
# Shared by the Polaris OIDC filter, JupyterHub, and Airflow: any product's four groups.
GROUP_PATTERN = re.compile(r"^role-([a-z][a-z0-9]{1,19})-(owner|developer|analyst|writer)$")
DATABASE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
BUCKET_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$")
WRITER_PATTERN = re.compile(r"^srv-[a-z0-9][a-z0-9-]{1,40}$")
TOP_LEVEL_KEYS = (
    "apiVersion",
    "name",
    "description",
    "environments",
    "groups",
    "access",
    "materialized_views",
    "apps",
    "writer_user",
)
ENVIRONMENT_KEYS = ("catalog", "namespace", "bucket", "mv_database")
OPTIONAL_TOP_LEVEL_KEYS = ("repo",)
REPO_KEYS = ("url", "prod_branch", "uat_branch")
# Airflow Git bundles: <name>-main (prod branch) and <name>-uat (UAT branch).
BUNDLE_ENVIRONMENTS = (("main", "prod_branch"), ("uat", "uat_branch"))
BUNDLE_CLASSPATH = "airflow.providers.git.bundles.git.GitDagBundle"
BUNDLE_KWARGS = {"git_conn_id": "lakehouse_git", "refresh_interval": 300, "sparse_dirs": ["dags", "configs", "notebooks"]}
# DAG IDs start with their bundle name, so the product (and its writer) follows from the ID.
DAG_ID_PATTERN = re.compile(r"^(?P<product>[a-z][a-z0-9]{1,19})-(?P<env>main|uat)-(?P<workload>.+)$")
BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,99}$")
URL_SAFE = re.compile(r"^[A-Za-z0-9._~/%-]+$")
# Pull request discovery (the Jenkins <name>_cd job) needs a github.com repository.
GITHUB_URL = re.compile(r"https://github\.com/(?P<owner>[A-Za-z0-9-]{1,39})/(?P<repository>[A-Za-z0-9._-]{1,100}?)(?:\.git)?/?")


class ProductError(Exception):
    """A validation or state failure; messages name files and fields, never secrets."""


@dataclass(frozen=True)
class Environment:
    key: str
    catalog: str
    namespace: str
    bucket: str
    mv_database: str


@dataclass(frozen=True)
class Repo:
    url: str
    prod_branch: str
    uat_branch: str


@dataclass(frozen=True)
class WriterUser:
    username: str
    password_file: str


@dataclass(frozen=True)
class Product:
    name: str
    description: str
    environments: tuple[Environment, ...]
    groups: dict[str, str]
    access: dict[str, dict[str, str]]
    materialized_views: dict[str, dict[str, str]]
    jupyterhub: tuple[str, ...]
    airflow: dict[str, str]
    jenkins: dict[str, tuple[str, ...]]
    writer_user: WriterUser
    path: Path | None = None
    repo: Repo | None = None

    def environment(self, key: str) -> Environment:
        return next(env for env in self.environments if env.key == key)

    def group(self, role: str) -> str:
        return self.groups[role]

    def group_names(self) -> tuple[str, ...]:
        return tuple(self.groups[role] for role in ROLES)

    def role_of_group(self, group: str) -> str | None:
        return next((role for role in ROLES if self.groups[role] == group), None)

    def buckets(self) -> tuple[str, ...]:
        return tuple(env.bucket for env in self.environments)

    @property
    def protected(self) -> bool:
        return self.name == DEFAULT_PRODUCT


def starrocks_role(group: str) -> str:
    """StarRocks role names use underscores: role-sales-owner -> role_sales_owner."""
    return group.replace("-", "_")


def catalog_role(group: str, catalog: str) -> str:
    """The Polaris catalog role binding one group to one catalog (the existing pattern)."""
    return f"{group}-{catalog}-catalog"


def allowed_location(env: Environment) -> str:
    return f"s3://{env.bucket}/{env.catalog}/"


def namespace_location(env: Environment) -> str:
    return f"s3://{env.bucket}/{env.catalog}/{env.namespace}/"


def validate_name(name: object) -> str:
    if name is None or isinstance(name, bool):
        # YAML 1.1 reads bare no, on, off, yes, true, false, and null as booleans or null.
        raise ProductError('The product name was read as a boolean or null; quote it, for example name: "no".')
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        raise ProductError("Product name must be 2-20 lowercase letters or digits, starting with a letter.")
    if name in RESERVED_NAMES:
        raise ProductError(f"Product name {name!r} is reserved.")
    return name


def _mapping(value: object, where: str, keys: tuple[str, ...], *, exact: bool = True) -> dict:
    if not isinstance(value, dict):
        raise ProductError(f"{where} must be a mapping.")
    unknown = sorted(str(key) for key in value if key not in keys)
    if unknown:
        raise ProductError(f"{where} has unknown keys: {', '.join(unknown)}.")
    missing = [key for key in keys if key not in value]
    if exact and missing:
        raise ProductError(f"{where} is missing keys: {', '.join(missing)}.")
    return value


def _text(value: object, where: str, pattern: re.Pattern[str] | None = None) -> str:
    if not isinstance(value, str) or not value:
        raise ProductError(f"{where} must be a non-empty string.")
    if pattern is not None and not pattern.fullmatch(value):
        raise ProductError(f"{where} does not match {pattern.pattern}.")
    return value


def _bucket(value: object, where: str) -> str:
    bucket = _text(value, where, BUCKET_PATTERN)
    if bucket.startswith("xn--") or bucket.endswith("-s3alias"):
        raise ProductError(f"{where} uses a reserved bucket prefix or suffix.")
    with contextlib.suppress(ValueError):
        ipaddress.ip_address(bucket)
        raise ProductError(f"{where} must not be an IP address.")
    return bucket


def _levels(value: object, where: str, allowed: tuple[str, ...]) -> dict[str, dict[str, str]]:
    table = _mapping(value, where, ROLES)
    result: dict[str, dict[str, str]] = {}
    for role in ROLES:
        row = _mapping(table[role], f"{where}.{role}", ENVIRONMENTS)
        for env in ENVIRONMENTS:
            if row[env] not in allowed:
                raise ProductError(f"{where}.{role}.{env} must be one of {', '.join(allowed)}.")
        result[role] = {env: row[env] for env in ENVIRONMENTS}
    return result


def parse_product(data: object, source: str = "<product>") -> Product:
    """Validate one product document (BR-1.1, BR-1.5) and return the model."""
    document = _mapping(data, source, TOP_LEVEL_KEYS + OPTIONAL_TOP_LEVEL_KEYS, exact=False)
    missing = [key for key in TOP_LEVEL_KEYS if key not in document]
    if missing:
        raise ProductError(f"{source} is missing keys: {', '.join(missing)}.")
    if document["apiVersion"] != API_VERSION:
        raise ProductError(f"{source}: apiVersion must be {API_VERSION}.")
    name = validate_name(document["name"])
    description = _text(document["description"], f"{source}.description")
    if len(description) > 200 or not description.isprintable():
        raise ProductError(f"{source}.description must be at most 200 printable characters.")

    envs = _mapping(document["environments"], f"{source}.environments", ENVIRONMENTS)
    environments = []
    for key in ENVIRONMENTS:
        where = f"{source}.environments.{key}"
        env = _mapping(envs[key], where, ENVIRONMENT_KEYS)
        if env["catalog"] != SHARED_CATALOGS[key]:
            raise ProductError(f"{where}.catalog must be the shared catalog {SHARED_CATALOGS[key]!r}.")
        environments.append(Environment(
            key=key,
            catalog=env["catalog"],
            namespace=_text(env["namespace"], f"{where}.namespace", DATABASE_PATTERN),
            bucket=_bucket(env["bucket"], f"{where}.bucket"),
            mv_database=_text(env["mv_database"], f"{where}.mv_database", DATABASE_PATTERN),
        ))
    if len({env.bucket for env in environments}) != len(environments):
        raise ProductError(f"{source}: each environment needs its own bucket.")
    if len({env.namespace for env in environments}) != len(environments):
        raise ProductError(f"{source}: each environment needs its own namespace.")
    if len({env.mv_database for env in environments}) != len(environments):
        raise ProductError(f"{source}: each environment needs its own MV database.")

    raw_groups = _mapping(document["groups"], f"{source}.groups", ROLES)
    groups: dict[str, str] = {}
    tokens = set()
    for role in ROLES:
        group = _text(raw_groups[role], f"{source}.groups.{role}")
        match = GROUP_PATTERN.fullmatch(group)
        if not match or match.group(2) != role:
            raise ProductError(f"{source}.groups.{role} must match role-<token>-{role}.")
        tokens.add(match.group(1))
        groups[role] = group
    if len(tokens) != 1:
        raise ProductError(f"{source}.groups must share one token, e.g. role-<token>-owner.")

    access = _levels(document["access"], f"{source}.access", DATA_LEVELS)
    materialized_views = _levels(document["materialized_views"], f"{source}.materialized_views", MV_LEVELS)

    apps = _mapping(document["apps"], f"{source}.apps", ("jupyterhub", "airflow", "jenkins"))
    jupyterhub = apps["jupyterhub"]
    if not isinstance(jupyterhub, list) or any(role not in ROLES for role in jupyterhub) or len(set(jupyterhub)) != len(jupyterhub):
        raise ProductError(f"{source}.apps.jupyterhub must be a list of distinct roles ({', '.join(ROLES)}).")
    airflow = _mapping(apps["airflow"], f"{source}.apps.airflow", ROLES, exact=False)
    for role, value in airflow.items():
        if value not in AIRFLOW_ROLES:
            raise ProductError(f"{source}.apps.airflow.{role} must be one of {', '.join(AIRFLOW_ROLES)}.")
    if isinstance(apps["jenkins"], dict) and "owner" in apps["jenkins"]:
        raise ProductError(f"{source}.apps.jenkins.owner is not allowed: the owner is always admin of the product's Jenkins folder.")
    jenkins_raw = _mapping(apps["jenkins"], f"{source}.apps.jenkins", JENKINS_ROLES, exact=False)
    jenkins: dict[str, tuple[str, ...]] = {}
    for role, permissions in jenkins_raw.items():
        if isinstance(permissions, list) and any(isinstance(item, str) and item.startswith("Overall/") for item in permissions):
            raise ProductError(f"{source}.apps.jenkins.{role}: global Jenkins rights (Overall/*) are not granted by product files.")
        if not isinstance(permissions, list) or not permissions or any(item not in JENKINS_PERMISSIONS for item in permissions):
            raise ProductError(f"{source}.apps.jenkins.{role} must be a non-empty list of allowed Jenkins folder permissions.")
        jenkins[role] = tuple(dict.fromkeys(permissions))

    writer = _mapping(document["writer_user"], f"{source}.writer_user", ("username", "password_file"))
    username = _text(writer["username"], f"{source}.writer_user.username", WRITER_PATTERN)
    password_file = _text(writer["password_file"], f"{source}.writer_user.password_file")
    parts = Path(password_file).parts
    if Path(password_file).is_absolute() or parts[:2] != (".runtime", "credentials") or len(parts) != 3 or ".." in parts:
        raise ProductError(f"{source}.writer_user.password_file must be .runtime/credentials/<file>.")

    return Product(
        name=name,
        description=description,
        environments=tuple(environments),
        groups=groups,
        access=access,
        materialized_views=materialized_views,
        jupyterhub=tuple(role for role in ROLES if role in jupyterhub),
        airflow={role: airflow[role] for role in ROLES if role in airflow},
        jenkins={role: jenkins[role] for role in JENKINS_ROLES if role in jenkins},
        writer_user=WriterUser(username, password_file),
        repo=_repo(document.get("repo"), f"{source}.repo") if "repo" in document else None,
    )


def _branch(value: object, where: str) -> str:
    branch = _text(value, where, BRANCH_PATTERN)
    if ".." in branch or "//" in branch or "@{" in branch or branch.endswith(("/", ".", ".lock")):
        raise ProductError(f"{where} is not a valid Git branch name.")
    return branch


def _repo(value: object, where: str) -> Repo:
    """A credential-free https repository and its prod and UAT branches (read anonymously)."""
    repo = _mapping(value, where, REPO_KEYS)
    url = _text(repo["url"], f"{where}.url")
    parts = urllib.parse.urlsplit(url)
    if (
        len(url) > 300 or parts.scheme != "https" or not parts.hostname or parts.username or parts.password
        or parts.port or parts.query or parts.fragment or not URL_SAFE.fullmatch(parts.hostname + parts.path)
        or not parts.path.strip("/")
    ):
        raise ProductError(f"{where}.url must be a credential-free https URL (no user, password, port, query, or fragment).")
    return Repo(url=url, prod_branch=_branch(repo["prod_branch"], f"{where}.prod_branch"),
                uat_branch=_branch(repo["uat_branch"], f"{where}.uat_branch"))


def github_repository(url: str) -> tuple[str, str] | None:
    """(owner, repository) for an https://github.com/<owner>/<repository>[.git][/] URL, else None."""
    match = GITHUB_URL.fullmatch(url)
    if not match or match["repository"] in (".", "..", ".git"):
        return None
    return match["owner"], match["repository"]


def bundle_names(product: Product) -> dict[str, str]:
    return {env: f"{product.name}-{env}" for env, _ in BUNDLE_ENVIRONMENTS}


def bundle_config(products: list[Product]) -> list[dict]:
    """The Airflow Git bundle list: two bundles per product with a repo, default first."""
    ordered = sorted(products, key=lambda product: (not product.protected, product.name))
    bundles = []
    for product in ordered:
        if product.repo is None:
            continue
        for env, branch_field in BUNDLE_ENVIRONMENTS:
            bundles.append({
                "name": f"{product.name}-{env}",
                "classpath": BUNDLE_CLASSPATH,
                "kwargs": {"repo_url": product.repo.url, "tracking_ref": getattr(product.repo, branch_field), **BUNDLE_KWARGS},
            })
    return bundles


def product_for_dag_id(dag_id: object) -> tuple[str, str] | None:
    """(product, 'main' | 'uat') from a DAG ID such as default-main-test_environment, else None."""
    if not isinstance(dag_id, str):
        return None
    match = DAG_ID_PATTERN.fullmatch(dag_id)
    if not match or match.group("product") in RESERVED_NAMES:
        return None
    return match.group("product"), match.group("env")


def load_product(path: Path) -> Product:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ProductError(f"Product file is unavailable: {path.name}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise ProductError(f"Product file {path.name} is not valid YAML.") from error
    product = parse_product(data, path.name)
    if path.name != f"{product.name}.yaml":
        raise ProductError(f"Product file {path.name} must be named {product.name}.yaml.")
    return replace(product, path=path)


def product_file(name: str, directory: Path | None = None) -> Path:
    return Path(directory or PRODUCTS_DIR) / f"{validate_name(name)}.yaml"


def check_collisions(products: list[Product]) -> None:
    """No two products share a bucket, namespace, MV database, group token, or writer (BR-1.2)."""
    owners: dict[tuple[str, str], str] = {}
    for product in products:
        token = GROUP_PATTERN.fullmatch(product.groups["owner"]).group(1)
        keys = [("product name", product.name), ("group token", token), ("writer user", product.writer_user.username)]
        keys += [("bucket", env.bucket) for env in product.environments]
        keys += [("namespace", env.namespace) for env in product.environments]
        keys += [("MV database", env.mv_database) for env in product.environments]
        for kind, value in dict.fromkeys(keys):
            other = owners.setdefault((kind, value), product.name)
            if other != product.name:
                raise ProductError(f"Products {other!r} and {product.name!r} share the {kind} {value!r}.")


def load_all(directory: Path | None = None) -> list[Product]:
    """Every product file, ``default`` first, then by name; collisions are refused."""
    directory = Path(directory or PRODUCTS_DIR)
    if not directory.is_dir():
        raise ProductError("The data product directory is unavailable.")
    products = [load_product(path) for path in sorted(directory.glob("*.yaml"))]
    products.sort(key=lambda product: (not product.protected, product.name))
    check_collisions(products)
    return products


def render_template(name: str) -> str:
    """The standard product file for ``--init`` (the default conventions applied to name)."""
    validate_name(name)
    text = TEMPLATE_FILE.read_text(encoding="utf-8").replace("{name}", name)
    parse_product(yaml.safe_load(text), f"{name}.yaml")
    return text


# ---- applied state (CR-Q6: names are locked once applied) ----

LOCKED_FIELDS = ("namespace", "bucket", "mv_database")


def state_document(product: Product) -> dict:
    return {
        "name": product.name,
        "environments": {env.key: {field: getattr(env, field) for field in LOCKED_FIELDS} for env in product.environments},
        "groups": dict(product.groups),
        "writer_user": product.writer_user.username,
    }


def state_path(name: str, state_dir: Path | None = None) -> Path:
    return Path(state_dir or STATE_DIR) / f"{validate_name(name)}.json"


def read_state(name: str, state_dir: Path | None = None) -> dict | None:
    path = state_path(name, state_dir)
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file():
        raise ProductError(f"Applied state for {name!r} is not a regular file.")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ProductError(f"Applied state for {name!r} is unreadable.") from error


def write_state(product: Product, state_dir: Path | None = None) -> Path:
    path = state_path(product.name, state_dir)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    document = state_document(product) | {"applied_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    descriptor, temporary = tempfile.mkstemp(prefix=f".{product.name}.", dir=path.parent)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(document, stream, indent=2, sort_keys=True)
        stream.write("\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    return path


def check_locked_names(product: Product, state: dict | None) -> None:
    """Refuse a renamed bucket, namespace, MV database, group, or writer user (BR-1.3)."""
    if state is None:
        return
    current = state_document(product)
    changed = [
        f"environments.{env}.{field}"
        for env in ENVIRONMENTS
        for field in LOCKED_FIELDS
        if (state.get("environments") or {}).get(env, {}).get(field) != current["environments"][env][field]
    ]
    changed += [f"groups.{role}" for role in ROLES if (state.get("groups") or {}).get(role) != current["groups"][role]]
    if state.get("writer_user") != current["writer_user"]:
        changed.append("writer_user.username")
    if changed:
        raise ProductError(
            f"Product {product.name!r} was applied with other names ({', '.join(changed)}); "
            "names are locked once applied. Remove the product and create it again to rename."
        )


def product_from_state(state: dict) -> Product:
    """A minimal model rebuilt from the applied state, for removal when the file is gone."""
    name = validate_name(state.get("name"))
    environments = tuple(
        Environment(key, SHARED_CATALOGS[key], **{field: state["environments"][key][field] for field in LOCKED_FIELDS})
        for key in ENVIRONMENTS
    )
    none = {role: {env: "none" for env in ENVIRONMENTS} for role in ROLES}
    return Product(
        name=name,
        description=f"{name} (from applied state)",
        environments=environments,
        groups={role: state["groups"][role] for role in ROLES},
        access=none,
        materialized_views=none,
        jupyterhub=(),
        airflow={},
        jenkins={},
        writer_user=WriterUser(state["writer_user"], f".runtime/credentials/{state['writer_user']}-password"),
    )


@contextlib.contextmanager
def operation_lock(state_dir: Path | None = None) -> Iterator[None]:
    """One apply or remove at a time; a stale lock is reported, never removed (BR-10)."""
    lock = Path(state_dir or STATE_DIR) / ".lock"
    lock.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError as error:
        age = int(time.time() - lock.stat().st_mtime)
        raise ProductError(
            f"Another data product operation holds {lock} (age {age}s). "
            "If no operation is running, remove that directory and retry."
        ) from error
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            lock.rmdir()


# ---- helpers for the app sign-in hooks ----

def product_groups(products: list[Product]) -> frozenset[str]:
    return frozenset(group for product in products for group in product.group_names())


def owner_groups(products: list[Product]) -> tuple[str, ...]:
    return tuple(product.groups["owner"] for product in products)


def jupyterhub_groups(products: list[Product]) -> frozenset[str]:
    """Groups admitted to JupyterHub, with the platform administrator (BR-6)."""
    return frozenset({PLATFORM_ADMIN_GROUP} | {product.groups[role] for product in products for role in product.jupyterhub})


def airflow_group_roles(products: list[Product]) -> dict[str, str]:
    """Group -> Airflow role across every product, with the platform administrator as Admin."""
    mapping = {product.groups[role]: value for product in products for role, value in product.airflow.items()}
    mapping[PLATFORM_ADMIN_GROUP] = "Admin"
    return mapping


def resolve_products(paths: list[Path], *, removal: bool = False, directory: Path | None = None) -> tuple[list[Product], list[Product]]:
    """The products named by ``--product`` (default: every file) and every product file.

    For a removal the named product may exist only as applied state, because the
    file is deleted last and a failed removal is rerun after that.
    """
    every = load_all(directory)
    if not paths:
        return every, every
    selected = []
    for path in paths:
        path = Path(path)
        if path.exists():
            selected.append(load_product(path))
            continue
        state = read_state(path.stem) if removal and NAME_PATTERN.fullmatch(path.stem) else None
        if state is None:
            raise ProductError(f"Unknown data product: {path.name} has no file and no applied state.")
        selected.append(product_from_state(state))
    if not removal:
        check_collisions(list({product.name: product for product in every + selected}.values()))
    return selected, every


def remaining_products(every: list[Product], removed: Product) -> list[Product]:
    return [product for product in every if product.name != removed.name]
