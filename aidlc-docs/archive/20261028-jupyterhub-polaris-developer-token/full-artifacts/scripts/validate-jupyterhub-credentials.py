#!/usr/bin/env python3
"""Validate protected JupyterHub OIDC and auth-state credentials."""

import os
import stat
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREDENTIALS = Path(os.environ.get("JUPYTER_CREDENTIALS_DIR", ROOT / ".runtime/credentials"))
EXPECTED_UID = int(os.environ.get("JUPYTER_HOST_UID", os.getuid()))
REQUIRED = {
    "jupyterhub-oidc-client-secret": 64,
    "jupyterhub-auth-state-crypt-key": 64,
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_file(name: str, length: int) -> None:
    path = CREDENTIALS / name
    if path.is_symlink() or not path.is_file():
        fail(f"Missing or unsafe credential file: {name}")
    metadata = path.stat()
    mode = stat.S_IMODE(metadata.st_mode)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != EXPECTED_UID:
        fail(f"Credential owner or file type is unsafe: {name}")
    if mode & 0o077 or metadata.st_size == 0:
        fail(f"Credential permissions or contents are unsafe: {name}")
    value = path.read_text(encoding="utf-8").strip()
    if len(value) != length or any(char not in "0123456789abcdefABCDEF" for char in value):
        fail(f"Credential format is invalid: {name}")


def main() -> None:
    if CREDENTIALS.is_symlink() or not CREDENTIALS.is_dir():
        fail("The credential directory is missing or unsafe.")
    for filename, length in REQUIRED.items():
        check_file(filename, length)
    print("JupyterHub OIDC and auth-state credential checks passed.")


if __name__ == "__main__":
    main()
