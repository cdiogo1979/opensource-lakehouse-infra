#!/usr/bin/env python3
"""Set and verify the password for the disposable StarRocks LDAP-test FE root."""

from __future__ import annotations

import importlib.util
import shutil
import stat
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SECRET_DIR = ROOT / ".runtime/starrocks-ldap-test/secrets"
FE_CONTAINER = "starrocks-ldap-test-fe"


def load_guard():
    path = ROOT / "infra/starrocks/ldap-access/bootstrap_roles.py"
    spec = importlib.util.spec_from_file_location("starrocks_ldap_bootstrap", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the isolated FE guard.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_secret(path: Path) -> str:
    if path.is_symlink() or stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise RuntimeError("The test-only root password file must be a regular mode-0600 file.")
    value = path.read_text(encoding="utf-8").strip()
    if not value or any(char not in "0123456789abcdef" for char in value):
        raise RuntimeError("The test-only root password file is invalid.")
    return value


def run(args: list[str], sql: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, input=sql, capture_output=True, text=True, check=False, timeout=20)


def main() -> int:
    try:
        guard = load_guard()
        guard.validate_target()
        docker = shutil.which("docker")
        if docker is None:
            raise RuntimeError("Docker CLI is unavailable.")
        password = read_secret(SECRET_DIR / "mysql-root-password")
        init_client = [docker, "exec", "-i", FE_CONTAINER, "mysql", "--protocol=TCP",
                       "--host=127.0.0.1", "--port=9030", "--user=root", "--connect-timeout=5",
                       "--ssl-mode=VERIFY_CA", "--ssl-ca=/run/sql-tls/starrocks-test.crt",
                       "--batch", "--silent"]
        escaped = password.replace("\\", "\\\\").replace("'", "''")
        initialized = run(init_client, f"SET PASSWORD = PASSWORD('{escaped}');\n")
        if initialized.returncode != 0:
            raise RuntimeError("Could not initialize the disposable FE root password; client output was suppressed.")
        verify = run([docker, "exec", FE_CONTAINER, "mysql",
                      "--defaults-extra-file=/run/admin/mysql-admin.cnf", "--protocol=TCP",
                      "--host=127.0.0.1", "--port=9030", "--connect-timeout=5", "--batch", "--silent",
                      "--execute=SELECT 1;"])
        if verify.returncode != 0:
            raise RuntimeError("The disposable FE admin TLS connection did not verify; client output was suppressed.")
        print("Disposable StarRocks FE root password set and TLS admin connection verified.")
        return 0
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
