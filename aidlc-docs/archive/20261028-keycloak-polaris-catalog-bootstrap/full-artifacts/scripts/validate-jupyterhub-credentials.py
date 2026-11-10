#!/usr/bin/env python3
"""Validate Hub identity source-file ownership and permissions on the host."""

import json
import os
import stat
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREDENTIALS = Path(
    os.environ.get("JUPYTER_CREDENTIALS_DIR", ROOT / ".runtime/credentials")
)
REGISTRY = Path(
    os.environ.get(
        "JUPYTER_IDENTITY_REGISTRY",
        ROOT / "infra/jupyter/hub/user-identities.json",
    )
)
EXPECTED_UID = int(os.environ.get("JUPYTER_HOST_UID", os.getuid()))


def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_file(relative_path, secret=False):
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        fail(f"Invalid credential path: {relative_path}")
    path = CREDENTIALS / relative
    if path.is_symlink() or not path.is_file():
        fail(f"Missing or unsafe credential file: {relative_path}")
    metadata = path.stat()
    mode = stat.S_IMODE(metadata.st_mode)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != EXPECTED_UID:
        fail(f"Credential owner or file type is unsafe: {relative_path}")
    if mode & 0o007 or mode & 0o020 or (secret and mode & 0o077):
        fail(f"Credential permissions are unsafe: {relative_path}")
    if metadata.st_size == 0:
        fail(f"Credential file is empty: {relative_path}")


def main():
    if CREDENTIALS.is_symlink() or not CREDENTIALS.is_dir():
        fail("The credential directory is missing or unsafe.")
    try:
        identities = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        fail("The JupyterHub identity registry is unreadable or invalid.")

    for identity in identities.values():
        for field in ("keytab", "rustfs_access", "rustfs_secret"):
            filename = identity.get(field)
            if not isinstance(filename, str):
                fail("The JupyterHub identity registry has an invalid credential mapping.")
            relative = Path("keytabs") / filename if field == "keytab" else Path(filename)
            check_file(relative)

    check_file("freeipa-jupyterhub-ldap-reader-password", secret=True)
    check_file("jupyterhub-auth-state-crypt-key", secret=True)
    print("JupyterHub credential ownership and permission checks passed.")


if __name__ == "__main__":
    main()
