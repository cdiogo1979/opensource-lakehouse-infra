#!/usr/bin/env python3
"""Render local Hive Metastore configuration without exposing its password."""

from pathlib import Path
from xml.sax.saxutils import escape
import os
import re
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PASSWORD_FILE = ROOT / ".runtime/credentials/postgres-password"
RUSTFS_IDENTITY_READY = ROOT / ".runtime/identity-provisioning/rustfs-ready"
if RUSTFS_IDENTITY_READY.exists():
    RUSTFS_ACCESS_FILE = ROOT / ".runtime/credentials/rustfs-hive-access-key"
    RUSTFS_SECRET_FILE = ROOT / ".runtime/credentials/rustfs-hive-secret-key"
else:
    RUSTFS_ACCESS_FILE = ROOT / ".runtime/credentials/rustfs-access-key"
    RUSTFS_SECRET_FILE = ROOT / ".runtime/credentials/rustfs-secret-key"
TEMPLATE = ROOT / "infra/hive/hive-site.xml.in"
OUTPUT = ROOT / ".runtime/hive-conf/hive-site.xml"
CORE_TEMPLATE = ROOT / "infra/hive/core-site.xml.in"
CORE_OUTPUT = ROOT / ".runtime/hive-conf/core-site.xml"


def main() -> None:
    secrets = {
        "@HIVE_DB_PASSWORD_XML@": PASSWORD_FILE,
        "@RUSTFS_ACCESS_KEY_XML@": RUSTFS_ACCESS_FILE,
        "@RUSTFS_SECRET_KEY_XML@": RUSTFS_SECRET_FILE,
    }
    realm = "LAKEHOUSE.LOCAL"
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("KERBEROS_REALM="):
                realm = line.partition("=")[2].strip() or realm

    rendered = TEMPLATE.read_text(encoding="utf-8")
    for token, path in secrets.items():
        value = path.read_text(encoding="utf-8").strip()
        if not value:
            raise SystemExit(f"ERROR: Required local credential is empty: {path.name}")
        rendered = rendered.replace(token, escape(value))
    rendered = rendered.replace(
        "@HIVE_SERVICE_PRINCIPAL_XML@",
        escape(f"hive/_HOST@{realm}"),
    )
    if re.search(r"@[A-Z0-9_]+@", rendered):
        raise SystemExit("ERROR: Hive configuration contains an unresolved template token.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    # The parent remains inside .runtime (mode 0700); the mounted service user
    # can read the file without making the host-side directory public.
    os.chmod(OUTPUT.parent, 0o755)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=OUTPUT.parent, delete=False
    ) as temporary:
        temporary.write(rendered)
        temp_path = Path(temporary.name)
    os.chmod(temp_path, 0o644)
    temp_path.replace(OUTPUT)

    core_rendered = CORE_TEMPLATE.read_text(encoding="utf-8")
    CORE_OUTPUT.write_text(core_rendered, encoding="utf-8")
    os.chmod(CORE_OUTPUT, 0o644)


if __name__ == "__main__":
    main()
