"""Shared StarRocks model, SQL quoting, and transports for the lakehouse bootstraps.

The access model mirrors the Polaris product matrix. SQL always travels over
stdin and client output is captured, never echoed, so passwords, the catalog
secret, and grant details stay out of terminal output and process arguments.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

ROOT = Path(__file__).resolve().parents[2]
CREDENTIALS = ROOT / ".runtime" / "credentials"
FE_CONTAINER = "lakehouse-local-starrocks-fe-1"
FE_HOST = "starrocks-fe"
QUERY_PORT = 9030


# The product model lives next to this package (infra/products on the host,
# /opt/lakehouse/products in the reconciler image).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "products"))
import data_products  # noqa: E402


@dataclass(frozen=True)
class Environment:
    name: str
    catalog: str
    namespace: str
    bucket: str
    mv_database: str


@dataclass(frozen=True)
class RoleScope:
    """One managed role's access in one shared catalog and its MV database.

    ``database`` None means catalog-wide (the platform administrator).
    """

    role: str
    catalog: str
    database: str | None
    level: str
    mv_database: str
    mv_level: str


@dataclass(frozen=True)
class Model:
    environments: tuple[Environment, ...]  # the default product's, for the smoke check
    group_roles: dict[str, str]
    managed_roles: tuple[str, ...]
    scopes: tuple[RoleScope, ...]
    mv_databases: tuple[str, ...]


PLATFORM_ADMIN_GROUP = data_products.PLATFORM_ADMIN_GROUP
PLATFORM_ADMIN_ROLE = "role_platform_admin"
PLATFORM_ADMIN_BUILTINS = ("user_admin", "db_admin", "cluster_admin")
SERVICE_ACCOUNT_PREFIX = "service-account-"
LEVELS = ("none", "read", "write", "manage")
INTERNAL_CATALOG = "default_catalog"


def environments_of(product) -> tuple[Environment, ...]:
    return tuple(Environment(e.key, e.catalog, e.namespace, e.bucket, e.mv_database) for e in product.environments)


def build_model(products: list) -> Model:
    """Roles and scopes for every product (BR-3); the platform administrator manages every catalog."""
    group_roles = {group: data_products.starrocks_role(group) for product in products for group in product.group_names()}
    group_roles[PLATFORM_ADMIN_GROUP] = PLATFORM_ADMIN_ROLE
    scopes = [
        RoleScope(
            data_products.starrocks_role(product.groups[role]), env.catalog, env.namespace,
            product.access[role][env.key], env.mv_database, product.materialized_views[role][env.key],
        )
        for product in products
        for role in data_products.ROLES
        for env in product.environments
    ]
    mv_databases = tuple(env.mv_database for product in products for env in product.environments)
    for catalog in data_products.SHARED_CATALOGS.values():
        scopes.append(RoleScope(PLATFORM_ADMIN_ROLE, catalog, None, "manage", "", "none"))
    for database in mv_databases:
        scopes.append(RoleScope(PLATFORM_ADMIN_ROLE, INTERNAL_CATALOG, None, "none", database, "manage"))
    default = next((product for product in products if product.protected), None)
    return Model(
        environments=environments_of(default) if default else (),
        group_roles=group_roles,
        managed_roles=tuple(dict.fromkeys(group_roles.values())),
        scopes=tuple(scopes),
        mv_databases=mv_databases,
    )


try:
    PRODUCTS = data_products.load_all()
    PRODUCT_ERROR: Exception | None = None
except data_products.ProductError as error:
    PRODUCTS, PRODUCT_ERROR = [], error
MODEL = build_model(PRODUCTS)
ENVIRONMENTS = MODEL.environments
# Keycloak group -> StarRocks role (underscores).
GROUP_ROLES = MODEL.group_roles
MANAGED_ROLES = MODEL.managed_roles


class StarRocksError(Exception):
    """A safe failure: names an operation or object, never SQL output or secrets."""


def require_products() -> None:
    """Refuse to change anything while a product file is invalid (BR-6, flow E)."""
    if PRODUCT_ERROR is not None:
        raise StarRocksError(f"The data product files are invalid: {PRODUCT_ERROR}")


def starrocks_enabled(env_file: Path = ROOT / ".env") -> bool:
    """STARROCKS_ENABLED from the environment, then .env; enabled unless 'false'."""
    value = os.environ.get("STARROCKS_ENABLED")
    if value is None and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, separator, text = line.partition("=")
            if separator and key.strip() == "STARROCKS_ENABLED":
                value = text.strip()
    return (value or "true").strip().lower() != "false"


def read_secret(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise StarRocksError(f"Protected file is unavailable: {path.name}")
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise StarRocksError(f"Protected file is empty: {path.name}")
    return value


def quote_identifier(name: str) -> str:
    if not name or any(ch in name for ch in "\x00\r\n"):
        raise StarRocksError("Invalid SQL identifier.")
    return "`" + name.replace("`", "``") + "`"


def quote_literal(value: str) -> str:
    if "\x00" in value:
        raise StarRocksError("Invalid SQL literal.")
    escaped = value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")
    return "'" + escaped + "'"


def user_identity(name: str) -> str:
    return f"{quote_literal(name)}@'%'"


_BATCH_ESCAPES = {"\\t": "\t", "\\n": "\n", "\\\\": "\\", "\\0": "\x00"}


def parse_batch_output(text: str) -> list[dict[str, str]]:
    """Parse `mysql --batch` output (header row, tab separated, backslash escaped)."""
    lines = [line for line in text.split("\n") if line != ""]
    if not lines:
        return []
    unescape = lambda field: re.sub(r"\\[tn\\0]", lambda m: _BATCH_ESCAPES[m.group(0)], field)
    header = [unescape(field) for field in lines[0].split("\t")]
    return [dict(zip(header, (unescape(field) for field in line.split("\t")))) for line in lines[1:]]


class SqlRunner(Protocol):
    def query(self, sql: str, operation: str) -> list[dict[str, str]]: ...

    def execute(self, sql: str, operation: str) -> None: ...


class _ClientRunner:
    """Runs a MySQL-protocol client with SQL on stdin and the password in MYSQL_PWD."""

    def __init__(self, password: str | None) -> None:
        self.password = password

    def _command(self) -> list[str]:
        raise NotImplementedError

    def _run(self, sql: str, operation: str) -> str:
        env = dict(os.environ)
        env.pop("MYSQL_PWD", None)
        if self.password:
            env["MYSQL_PWD"] = self.password
        try:
            result = subprocess.run(self._command(), input=sql, capture_output=True, text=True, env=env, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise StarRocksError(f"StarRocks client unavailable during: {operation}") from error
        if result.returncode != 0:
            raise StarRocksError(f"StarRocks statement failed during: {operation}")
        return result.stdout

    def query(self, sql: str, operation: str) -> list[dict[str, str]]:
        return parse_batch_output(self._run(sql, operation))

    def execute(self, sql: str, operation: str) -> None:
        self._run(sql, operation)


class DockerExecRunner(_ClientRunner):
    """Host transport: the FE image's bundled mysql client through `docker exec`."""

    def __init__(self, password: str | None, container: str = FE_CONTAINER) -> None:
        super().__init__(password)
        self.container = container

    def _command(self) -> list[str]:
        # `-e MYSQL_PWD` copies the value from this process's environment, so it
        # never appears in the command line.
        command = ["docker", "exec", "-i"]
        if self.password:
            command += ["-e", "MYSQL_PWD"]
        return command + [self.container, "mysql", "--batch", "-h127.0.0.1", f"-P{QUERY_PORT}", "-uroot"]


class NetworkRunner(_ClientRunner):
    """In-container transport: a local mysql/mariadb client to the FE over the network."""

    def __init__(self, password: str | None, host: str = FE_HOST, port: int = QUERY_PORT) -> None:
        super().__init__(password)
        self.host, self.port = host, port

    def _command(self) -> list[str]:
        # The reconciler image ships the MariaDB client, whose 11.x line turns TLS
        # on by default; the StarRocks query port on the internal network is plain.
        return ["mysql", "--batch", "--skip-ssl", f"-h{self.host}", f"-P{self.port}", "-uroot"]


def make_runner(transport: str, password: str | None) -> SqlRunner:
    if transport == "docker":
        return DockerExecRunner(password)
    if transport == "network":
        return NetworkRunner(password)
    raise StarRocksError(f"Unknown transport: {transport}")


def root_runner(transport: str, password_file: Path, timeout_seconds: int = 0) -> SqlRunner:
    """A runner authenticated as root with the protected password, waiting for the FE."""
    runner = make_runner(transport, read_secret(password_file))
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            runner.query("SELECT 1;", "root login")
            return runner
        except StarRocksError:
            if time.monotonic() >= deadline:
                raise StarRocksError("StarRocks root login failed; is StarRocks running and bootstrapped?") from None
            time.sleep(3)
