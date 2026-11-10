"""Shared StarRocks model, SQL quoting, and transports for the lakehouse bootstraps.

The access model mirrors the Polaris product matrix. SQL always travels over
stdin and client output is captured, never echoed, so passwords, the catalog
secret, and grant details stay out of terminal output and process arguments.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

ROOT = Path(__file__).resolve().parents[2]
CREDENTIALS = ROOT / ".runtime" / "credentials"
FE_CONTAINER = "lakehouse-local-starrocks-fe-1"
FE_HOST = "starrocks-fe"
QUERY_PORT = 9030


@dataclass(frozen=True)
class Environment:
    name: str
    catalog: str
    namespace: str
    bucket: str
    mv_database: str


ENVIRONMENTS = (
    Environment("prod", "lakehouse", "default_lh", "bucket-default", "default_lh"),
    Environment("uat", "lakehouse_uat", "default_lhuat", "bucket-default-uat", "default_lhuat"),
    Environment("dev", "lakehouse_dev", "default_lhdev", "bucket-default-dev", "default_lhdev"),
)

# Keycloak group -> StarRocks role (underscores; FR-5).
GROUP_ROLES = {
    "role-default-owner": "role_default_owner",
    "role-default-developer": "role_default_developer",
    "role-default-analyst": "role_default_analyst",
    "role-default-writer": "role_default_writer",
    "role-platform-admin": "role_platform_admin",
}
MANAGED_ROLES = tuple(GROUP_ROLES.values())
PLATFORM_ADMIN_GROUP = "role-platform-admin"
PLATFORM_ADMIN_BUILTINS = ("user_admin", "db_admin", "cluster_admin")
SERVICE_ACCOUNT_PREFIX = "service-account-"

LEVELS = ("none", "read", "write", "manage")
CATALOG_MATRIX = {
    "role_default_owner": {"prod": "manage", "uat": "manage", "dev": "manage"},
    "role_default_developer": {"prod": "read", "uat": "read", "dev": "write"},
    "role_default_analyst": {"prod": "read", "uat": "none", "dev": "none"},
    "role_default_writer": {"prod": "write", "uat": "write", "dev": "write"},
    "role_platform_admin": {"prod": "manage", "uat": "manage", "dev": "manage"},
}
MV_MATRIX = {
    "role_default_owner": {"prod": "manage", "uat": "manage", "dev": "manage"},
    "role_default_developer": {"prod": "read", "uat": "read", "dev": "read"},
    "role_default_analyst": {"prod": "read", "uat": "none", "dev": "none"},
    "role_default_writer": {"prod": "author", "uat": "author", "dev": "author"},
    "role_platform_admin": {"prod": "manage", "uat": "manage", "dev": "manage"},
}
INTERNAL_CATALOG = "default_catalog"


class StarRocksError(Exception):
    """A safe failure: names an operation or object, never SQL output or secrets."""


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
