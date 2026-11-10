"""Source contracts for the RustFS OIDC Compose wiring and secret wrapper."""

import os
import re
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = (ROOT / "compose.core.yml").read_text(encoding="utf-8")
WRAPPER = ROOT / "infra/rustfs/rustfs-entrypoint.sh"


def service(name: str) -> str:
    body = COMPOSE.split(f"\n  {name}:\n", 1)[1]
    return re.split(r"\n  [a-z][a-z0-9-]*:\n|\nnetworks:\n", body, maxsplit=1)[0]


def top_level_networks() -> str:
    return COMPOSE.split("\nnetworks:\n", 1)[1].split("\nvolumes:\n", 1)[0]


def test_rustfs_enables_keycloak_oidc_with_exact_settings():
    rustfs = service("rustfs")
    for line in (
        'RUSTFS_IDENTITY_OPENID_ENABLE: "on"',
        "RUSTFS_IDENTITY_OPENID_CONFIG_URL: http://keycloak.localhost:8080/realms/lakehouse/.well-known/openid-configuration",
        "RUSTFS_IDENTITY_OPENID_CLIENT_ID: rustfs",
        "RUSTFS_IDENTITY_OPENID_CLAIM_NAME: groups",
        'RUSTFS_IDENTITY_OPENID_REDIRECT_URI_DYNAMIC: "on"',
        "RUSTFS_IDENTITY_OPENID_DISPLAY_NAME: Keycloak",
        "RUSTFS_OUTBOUND_ALLOW_ORIGINS: http://keycloak.localhost:8080\n",
    ):
        assert line in rustfs
    assert "ROLE_POLICY" not in rustfs
    assert "RUSTFS_IDENTITY_OPENID_REDIRECT_URI:" not in rustfs


def test_client_secret_is_never_in_compose_configuration():
    assert "CLIENT_SECRET" not in COMPOSE
    rustfs = service("rustfs")
    assert "rustfs-oidc-client-secret:/run/secrets/rustfs_oidc_client_secret:ro" in rustfs
    assert "./infra/rustfs/rustfs-entrypoint.sh:/opt/lakehouse/rustfs-entrypoint.sh:ro" in rustfs
    assert "entrypoint: [/bin/sh, /opt/lakehouse/rustfs-entrypoint.sh]" in rustfs
    assert "command: [/data]" in rustfs


def test_root_credentials_ports_and_healthcheck_are_unchanged():
    rustfs = service("rustfs")
    assert "RUSTFS_ACCESS_KEY_FILE: /run/secrets/rustfs_access_key" in rustfs
    assert "RUSTFS_SECRET_KEY_FILE: /run/secrets/rustfs_secret_key" in rustfs
    assert "127.0.0.1:${RUSTFS_S3_HOST_PORT:-9000}:9000" in rustfs
    assert "127.0.0.1:${RUSTFS_CONSOLE_HOST_PORT:-9001}:9001" in rustfs
    assert "http://127.0.0.1:9000/health/ready" in rustfs


def test_keycloak_alias_exists_only_on_the_internal_identity_network():
    assert COMPOSE.count("keycloak.localhost]") == 1
    keycloak = service("keycloak")
    assert "      core: {}\n" in keycloak
    assert "      rustfs-identity:\n        aliases: [keycloak.localhost]" in keycloak
    assert "networks: [core, data-access, rustfs-identity]" in service("rustfs")
    members = [name for name in ("keycloak-db", "polaris-db", "polaris", "polaris-group-reconciler")
               if "rustfs-identity" in service(name)]
    assert members == []
    # The other modules never join the identity network either.
    for module in ("compose.jupyter.yml", "compose.jenkins.yml", "compose.starrocks.yml", "compose.airflow.yml"):
        assert "rustfs-identity" not in (ROOT / module).read_text(encoding="utf-8"), module
    networks = top_level_networks()
    identity = networks.split("  rustfs-identity:\n", 1)[1].split("\n  ", 1)[0]
    assert "name: lakehouse-local_rustfs-identity" in networks
    assert "internal: true" in networks.split("  rustfs-identity:\n", 1)[1]
    assert identity.strip().startswith("name: lakehouse-local_rustfs-identity")


def test_runtime_preparation_creates_and_stages_the_client_secret():
    source = (ROOT / "scripts/setup/prepare-runtime.py").read_text(encoding="utf-8")
    assert 'read_or_create("rustfs-oidc-client-secret", secrets.token_hex(32))' in source
    staging = source.split("for filename in (\n        \"rustfs-access-key\",", 1)[1].split("):", 1)[0]
    assert '"rustfs-oidc-client-secret"' in staging


def run_wrapper(tmp_path: Path, secret: str | None):
    secret_file = tmp_path / "client_secret"
    if secret is not None:
        secret_file.write_text(secret, encoding="utf-8")
    stub = tmp_path / "entrypoint.sh"
    stub.write_text(
        '#!/bin/sh\nprintf "args=%s\\n" "$*"\n'
        'printf "secret=%s\\n" "$RUSTFS_IDENTITY_OPENID_CLIENT_SECRET"\n'
        'printf "file_var=%s\\n" "${SECRET_FILE:-unset}"\n',
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    wrapper = tmp_path / "wrapper.sh"
    wrapper.write_text(
        WRAPPER.read_text(encoding="utf-8")
        .replace("/run/secrets/rustfs_oidc_client_secret", str(secret_file))
        .replace("exec /entrypoint.sh", f"exec {stub}"),
        encoding="utf-8",
    )
    env = {key: value for key, value in os.environ.items() if key != "RUSTFS_IDENTITY_OPENID_CLIENT_SECRET"}
    return subprocess.run(["/bin/sh", str(wrapper), "/data"], capture_output=True, text=True, env=env)


def test_wrapper_exports_secret_and_runs_the_stock_entrypoint(tmp_path):
    result = run_wrapper(tmp_path, "abc123\n")
    assert result.returncode == 0, result.stderr
    assert "args=/data" in result.stdout
    assert "secret=abc123" in result.stdout
    assert "file_var=unset" in result.stdout


def test_wrapper_refuses_missing_or_empty_secret_without_printing_it(tmp_path):
    for secret in (None, "", "\n"):
        result = run_wrapper(tmp_path, secret)
        assert result.returncode == 1
        assert "client secret file is" in result.stderr
        assert "args=" not in result.stdout
