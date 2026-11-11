"""Deploy a bundle's materialized views to StarRocks as the product's writer (mv-promotion).

A product repository declares MVs in ``materialized_views/<project>/<name>.sql``
(``spec.load_materialized_views``). For the bundle's environment, the deployer fills in
``${catalog}``, ``${namespace}`` and ``${mv_database}`` from the product file and makes
the MV database match the files:

- a file without an MV is created;
- a managed MV whose definition changed is replaced: the new definition is created as
  ``<name>__lakehouse_new`` and swapped in atomically, then the old one is dropped;
- a managed MV without a file is dropped;
- MVs made by hand (no marker in their comment) are never touched.

Managed MVs carry ``lakehouse-mv sha256=<digest>`` at the start of their comment. An MV
whose source table doesn't exist yet (StarRocks: "Unknown table") is skipped and created
by a later run. Statements run as the writer, logged in with its Keycloak access token,
so StarRocks' own grants bound what a definition can do. Planning is standard library
only; ``connect`` needs pymysql (in the Airflow image).
"""

from __future__ import annotations

import hashlib
import re
import ssl
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

MARKER = "lakehouse-mv sha256="
STAGING_SUFFIX = "__lakehouse_new"
DIGEST_LENGTH = 16
_HEAD = re.compile(r"(CREATE\s+MATERIALIZED\s+VIEW\s+)(\S+)(\s+COMMENT\s+'((?:[^'\\]|\\.)*)')?", re.IGNORECASE)


@dataclass(frozen=True)
class Placement:
    """Where one environment's MVs read from and live: the product file's values."""

    catalog: str
    namespace: str
    mv_database: str


@dataclass
class Plan:
    create: list[str] = field(default_factory=list)
    replace: list[str] = field(default_factory=list)
    drop: list[str] = field(default_factory=list)
    keep: list[str] = field(default_factory=list)
    foreign: list[str] = field(default_factory=list)  # hand-made MVs that have a file's name


@dataclass
class Report:
    created: list[str] = field(default_factory=list)
    replaced: list[str] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    foreign: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


def render(statement: str, placement: Placement) -> str:
    """The statement for one environment: the three placeholders filled in, nothing else changed."""
    return statement.replace("${catalog}", placement.catalog).replace("${namespace}", placement.namespace).replace("${mv_database}", placement.mv_database)


def digest(rendered: str) -> str:
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()[:DIGEST_LENGTH]


def deployable(rendered: str, target: str, version: str) -> str:
    """The statement as deployed: created as ``target``, with the marker at the start of its comment."""
    head = _HEAD.match(rendered)
    if head is None:
        raise ValueError("not a CREATE MATERIALIZED VIEW statement")
    own = head.group(4)
    comment = f"{MARKER}{version}" + (f"; {own}" if own else "")
    return f"{head.group(1)}{target} COMMENT '{comment}'" + rendered[head.end() :]


def managed_version(comment: str | None) -> str | None:
    """The digest a managed MV was deployed with; None for an MV made by hand."""
    if not comment or not comment.startswith(MARKER):
        return None
    return comment[len(MARKER) :].split(";", 1)[0].strip()


def plan(desired: Mapping[str, str], existing: Mapping[str, str | None]) -> Plan:
    """What makes the MV database match the files.

    Args:
        desired: MV name to the digest of its rendered definition.
        existing: MV name to its comment, for every MV in the database.
    """
    result = Plan()
    for name in sorted(desired):
        if name not in existing:
            result.create.append(name)
            continue
        version = managed_version(existing[name])
        if version is None:
            result.foreign.append(name)
        elif version == desired[name]:
            result.keep.append(name)
        else:
            result.replace.append(name)
    result.drop = sorted(name for name, comment in existing.items() if name not in desired and managed_version(comment) is not None and not name.endswith(STAGING_SUFFIX))
    return result


def _unknown_table(error: Exception) -> bool:
    return "Unknown table" in str(error)


def apply(cursor: Any, database: str, views: Mapping[str, str], log: Any) -> Report:
    """Make ``database`` match ``views`` (MV name to rendered definition) with ``cursor``; every outcome is reported."""
    cursor.execute(
        "SELECT m.TABLE_NAME, t.TABLE_COMMENT FROM information_schema.materialized_views m "
        "LEFT JOIN information_schema.tables t ON t.TABLE_SCHEMA = m.TABLE_SCHEMA AND t.TABLE_NAME = m.TABLE_NAME "
        "WHERE m.TABLE_SCHEMA = %s",
        (database,),
    )
    existing = {row[0]: row[1] for row in cursor.fetchall()}
    versions = {name: digest(sql) for name, sql in views.items()}
    work = plan(versions, existing)
    report = Report(unchanged=work.keep, foreign=work.foreign)
    for name in work.foreign:
        log.warning("MV %s.%s exists but was made by hand (no %s marker); left unchanged.", database, name, MARKER.strip())

    def run(sql: str) -> None:
        cursor.execute(sql)

    for name in work.create:
        try:
            run(deployable(views[name], f"{database}.{name}", versions[name]))
            report.created.append(name)
        except Exception as error:  # noqa: BLE001 - every MV is reported, then the task fails once
            (report.skipped if _unknown_table(error) else report.failed).append(name)
            log.warning("MV %s.%s not created: %s", database, name, error)
    for name in work.replace:
        staging = f"{database}.{name}{STAGING_SUFFIX}"
        try:
            run(f"DROP MATERIALIZED VIEW IF EXISTS {staging}")
            run(deployable(views[name], staging, versions[name]))
            run(f"ALTER MATERIALIZED VIEW {database}.{name} SWAP WITH {name}{STAGING_SUFFIX}")
            run(f"DROP MATERIALIZED VIEW IF EXISTS {staging}")
            report.replaced.append(name)
        except Exception as error:  # noqa: BLE001
            (report.skipped if _unknown_table(error) else report.failed).append(name)
            log.warning("MV %s.%s not replaced (the current one stays): %s", database, name, error)
    for name in work.drop:
        try:
            run(f"DROP MATERIALIZED VIEW IF EXISTS {database}.{name}")
            report.dropped.append(name)
        except Exception as error:  # noqa: BLE001
            report.failed.append(name)
            log.warning("MV %s.%s not dropped: %s", database, name, error)
    return report


class _OpenIdConnect:
    """MySQL's authentication_openid_connect_client, which StarRocks' JWT login asks for (probe P1)."""

    def __init__(self, connection: Any):
        self.connection = connection

    def authenticate(self, packet: Any) -> Any:
        token = self.connection.password
        token = token if isinstance(token, bytes) else token.encode("ascii")
        size = len(token)
        length = bytes([size]) if size < 251 else (bytes([0xFC]) + size.to_bytes(2, "little") if size < 65536 else bytes([0xFD]) + size.to_bytes(3, "little"))
        self.connection.write_packet(bytes([1]) + length + token)
        return self.connection._read_packet()


def connect(host: str, port: int, user: str, token: str, ca_file: str) -> Any:
    """A TLS connection to StarRocks as ``user``, logged in with its Keycloak access token."""
    import pymysql

    context = ssl.create_default_context(cafile=ca_file)
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=token,
        ssl=context,
        autocommit=True,
        connect_timeout=15,
        auth_plugin_map={b"authentication_openid_connect_client": _OpenIdConnect},
    )
