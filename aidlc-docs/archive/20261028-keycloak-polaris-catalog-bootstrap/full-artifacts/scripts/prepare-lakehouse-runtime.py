#!/usr/bin/env python3
"""Create missing local secrets and provider config without exposing their values."""

from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime"
CREDENTIALS = ROOT / ".runtime" / "credentials"
CONTAINER_MOUNTS = ROOT / ".runtime" / "container-mounts"
POLARIS_OIDC_TEMPLATE = ROOT / "infra" / "polaris" / "oidc.properties"


def create_once(path: Path, content: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise
    path.chmod(0o600)


def merge_managed_properties(path: Path, additions: str, removals: set[str] | None = None) -> None:
    """Update only named property keys while preserving protected unrelated values."""
    if path.is_symlink() or not path.is_file() or not os.access(path, os.R_OK):
        raise RuntimeError("A protected provider configuration file is unavailable")
    current = path.read_text(encoding="utf-8").splitlines()
    updates = {}
    for line in additions.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key.strip():
            raise RuntimeError("A managed provider property is malformed")
        updates[key.strip()] = f"{key.strip()}={value.strip()}"

    removals = removals or set()
    found = set()
    output = []
    for line in current:
        key, separator, _ = line.partition("=")
        normalized_key = key.strip() if separator else ""
        if normalized_key in removals:
            continue
        if normalized_key not in updates:
            output.append(line)
            continue
        if normalized_key in found:
            raise RuntimeError("A managed provider property is duplicated")
        output.append(updates[normalized_key])
        found.add(normalized_key)
    output.extend(updates[key] for key in updates if key not in found)

    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write("\n".join(output) + "\n")
        temporary.chmod(0o600)
        os.replace(temporary, path)
        path.chmod(0o600)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def read_or_create(name: str, value: str) -> str:
    path = CREDENTIALS / name
    try:
        create_once(path, value + "\n")
    except FileExistsError:
        pass
    if path.is_symlink() or not path.is_file() or not os.access(path, os.R_OK):
        raise RuntimeError(f"Required credential file is unavailable: {name}")
    path.chmod(0o600)
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0]:
        raise RuntimeError(f"Required credential file is empty: {name}")
    if re.fullmatch(r"[A-Fa-f0-9]+", lines[0]) is None:
        raise RuntimeError(f"Credential file has an invalid format: {name}")
    return lines[0]


def stage_readonly_mount(name: str) -> None:
    """Stage a container-readable copy under a host-private runtime directory."""
    source = CREDENTIALS / name
    destination = CONTAINER_MOUNTS / name
    if source.is_symlink() or not source.is_file() or not os.access(source, os.R_OK):
        raise RuntimeError(f"Required provider file is unavailable: {name}")

    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{name}.", dir=CONTAINER_MOUNTS)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(source.read_bytes())
        temporary.chmod(0o644)
        os.replace(temporary, destination)
        destination.chmod(0o644)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def main() -> None:
    RUNTIME.mkdir(mode=0o700, exist_ok=True)
    RUNTIME.chmod(0o700)
    CREDENTIALS.mkdir(mode=0o700, exist_ok=True)
    CREDENTIALS.chmod(0o700)
    CONTAINER_MOUNTS.mkdir(mode=0o700, exist_ok=True)
    if CONTAINER_MOUNTS.is_symlink() or not CONTAINER_MOUNTS.is_dir():
        raise RuntimeError("Container mount directory is unavailable")
    CONTAINER_MOUNTS.chmod(0o700)

    keycloak_password = read_or_create("keycloak-db-password", secrets.token_hex(32))
    polaris_password = read_or_create("polaris-db-password", secrets.token_hex(32))
    read_or_create("keycloak-admin-password", secrets.token_hex(32))
    read_or_create("platform-admin-password", secrets.token_hex(32))
    read_or_create("keycloak-writer-client-secret", secrets.token_hex(32))
    read_or_create("polaris-bootstrap-secret", secrets.token_hex(32))
    rustfs_access_key = read_or_create("rustfs-access-key", secrets.token_hex(10).upper())
    rustfs_secret_key = read_or_create("rustfs-secret-key", secrets.token_hex(20))

    keycloak_config = "\n".join((
        "db=postgres",
        "db-url=jdbc:postgresql://keycloak-db:5432/keycloak",
        "db-username=keycloak",
        f"db-password={keycloak_password}",
        "health-enabled=true",
        "http-enabled=true",
        "hostname=http://keycloak.localhost:8080",
        "hostname-strict=false",
        "",
    ))
    polaris_storage_config = "\n".join((
        f"polaris.storage.aws.access-key={rustfs_access_key}",
        f"polaris.storage.aws.secret-key={rustfs_secret_key}",
    ))
    polaris_config = "\n".join((
        "polaris.persistence.type=relational-jdbc",
        "quarkus.datasource.username=polaris",
        f"quarkus.datasource.password={polaris_password}",
        "quarkus.datasource.jdbc.url=jdbc:postgresql://polaris-db:5432/polaris?currentSchema=polaris_schema",
        "",
    )) + polaris_storage_config + "\n" + POLARIS_OIDC_TEMPLATE.read_text(encoding="utf-8")
    pgpass = f"polaris-db:5432:polaris:polaris:{polaris_password}\n"
    polaris_bootstrap_secret = (CREDENTIALS / "polaris-bootstrap-secret").read_text(encoding="utf-8").strip()
    polaris_bootstrap = json.dumps(
        {"lakehouse": {"client-id": "root", "client-secret": polaris_bootstrap_secret}},
        separators=(",", ":"),
    ) + "\n"

    for filename, content in (
        ("keycloak.conf", keycloak_config),
        ("polaris-application.properties", polaris_config),
        ("polaris-pgpass", pgpass),
        ("polaris-bootstrap-credentials", polaris_bootstrap),
    ):
        path = CREDENTIALS / filename
        try:
            create_once(path, content)
        except FileExistsError:
            if path.is_symlink() or not path.is_file() or not os.access(path, os.R_OK) or path.stat().st_size == 0:
                raise RuntimeError(f"Required provider configuration is unavailable: {filename}")
            path.chmod(0o600)

    merge_managed_properties(
        CREDENTIALS / "keycloak.conf",
        "hostname=http://keycloak.localhost:8080",
    )
    merge_managed_properties(
        CREDENTIALS / "polaris-application.properties",
        polaris_storage_config + "\n" + POLARIS_OIDC_TEMPLATE.read_text(encoding="utf-8"),
        removals={
            "polaris.oidc.principal-mapper.id-claim-path",
            "polaris.authentication.realm-lakehouse.type",
        },
    )

    for filename in (
        "rustfs-access-key",
        "rustfs-secret-key",
        "keycloak.conf",
        "polaris-application.properties",
        "keycloak-admin-password",
        "platform-admin-password",
        "keycloak-writer-client-secret",
        "polaris-bootstrap-secret",
        "polaris-bootstrap-credentials",
    ):
        stage_readonly_mount(filename)

    print("Protected local runtime files and per-service mounts are ready (values omitted).")


if __name__ == "__main__":
    main()
