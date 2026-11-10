"""Contracts for the separate StarRocks Compose file and its configuration."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = (ROOT / "compose.starrocks.yml").read_text(encoding="utf-8")
FE_DIGEST = "starrocks/fe-ubuntu:4.1.7@sha256:f6dd1491f0dd9bdcaeb29fac53c49727b20603d708530f0e5156cfd501425462"
BE_DIGEST = "starrocks/be-ubuntu:4.1.7@sha256:39f7320127c9924abb1f1ce0ba0583ab11989cbe5bd1bb6274ada6f89ba5740d"


def test_images_are_upstream_4_1_7_pinned_by_digest_without_a_build():
    assert f"image: {FE_DIGEST}" in COMPOSE and f"image: {BE_DIGEST}" in COMPOSE
    assert "build:" not in COMPOSE


def test_only_the_fe_publishes_ports_and_only_on_loopback():
    ports = re.findall(r"^\s+- (\S+:\$\{[A-Z_]+:-\d+\}:\d+)$", COMPOSE, re.M)
    assert ports == ["127.0.0.1:${STARROCKS_QUERY_PORT:-9030}:9030", "127.0.0.1:${STARROCKS_HTTP_PORT:-8030}:8030"]


def test_networks_volumes_and_limits():
    assert "networks: [core, data-access, starrocks]" in COMPOSE
    assert "networks: [data-access, starrocks]" in COMPOSE
    assert "name: lakehouse-local_starrocks" in COMPOSE and "internal: true" in COMPOSE
    assert "starrocks-fe-meta:/opt/starrocks/fe/meta" in COMPOSE and "starrocks-be-storage:/opt/starrocks/be/storage" in COMPOSE
    assert "mem_limit: ${STARROCKS_FE_MEMORY_LIMIT:-2g}" in COMPOSE and "mem_limit: ${STARROCKS_BE_MEMORY_LIMIT:-4g}" in COMPOSE


def test_no_secrets_in_compose_or_config():
    body = "\n".join(line for line in COMPOSE.splitlines() if not line.lstrip().startswith("#"))
    assert "secrets:" not in body and "environment:" not in body
    # Only the TLS keystore and its password file are mounted from the runtime, read-only.
    runtime_mounts = [line.strip() for line in body.splitlines() if ".runtime/" in line]
    assert runtime_mounts == [
        "- ./.runtime/container-mounts/starrocks-fe-keystore.p12:/run/secrets/starrocks_fe_keystore.p12:ro",
        "- ./.runtime/container-mounts/starrocks-keystore-password:/run/secrets/starrocks_keystore_password:ro",
    ]
    for name in ("fe.conf", "be.conf"):
        text = (ROOT / "infra/starrocks/conf" / name).read_text()
        assert not re.search(r"(?i)(password|secret|credential)\s*=", text), name


def test_fe_heap_stays_below_its_container_limit():
    fe = (ROOT / "infra/starrocks/conf/fe.conf").read_text()
    assert "-Xmx1280m" in fe and "8192m" not in fe


def test_env_example_and_deferred_inventory():
    env = (ROOT / ".env.example").read_text()
    for key in ("STARROCKS_ENABLED=true", "STARROCKS_QUERY_PORT=9030", "STARROCKS_HTTP_PORT=8030",
                "STARROCKS_FE_MEMORY_LIMIT=2g", "STARROCKS_BE_MEMORY_LIMIT=4g"):
        assert key in env


def test_fe_entrypoint_adds_tls_from_protected_files():
    assert "entrypoint: [/usr/bin/tini-static, --, /opt/lakehouse/fe-entrypoint.sh]" in COMPOSE
    entry = (ROOT / "infra/starrocks/fe-entrypoint.sh").read_text()
    assert "ssl_keystore_location = /run/secrets/starrocks_fe_keystore.p12" in entry
    assert "head -n 1 /run/secrets/starrocks_keystore_password" in entry and 'chmod 600 "$conf"' in entry
    assert "exec /opt/starrocks/fe/bin/start_fe.sh --host_type FQDN" in entry


def test_certificate_script_and_login_verify_the_server():
    script = (ROOT / "scripts/setup/prepare-starrocks-certificates.py").read_text()
    assert 'SAN = "DNS:starrocks-fe,DNS:localhost,IP:127.0.0.1"' in script and '"pkcs12", "-export"' in script
    login = (ROOT / "scripts/clients/starrocks-login.sh").read_text()
    assert "--ssl-mode=VERIFY_IDENTITY --ssl-ca=/run/starrocks-ca.crt" in login
    lakehouse = (ROOT / "scripts/lakehouse.sh").read_text()
    assert lakehouse.index("python3 scripts/setup/prepare-starrocks-certificates.py") < lakehouse.index('"${COMPOSE[@]}" up -d "${STARROCKS_SERVICES[@]}"')


def test_token_helper_for_jdbc_clients():
    helper = (ROOT / "scripts/clients/starrocks-token.sh").read_text()
    assert "client_id=starrocks" in helper and '"password@-"' in helper and '"refresh_token@-"' in helper
    assert "os.chmod(temporary, 0o600)" in helper and "os.replace(temporary, path)" in helper
    assert "refusing to write through a symlink" in helper and "read -r -s" in helper
    readme = (ROOT / "README.md").read_text()
    assert "**DBeaver and other JDBC clients**" in readme and "starrocks-token.sh --watch" in readme
    assert "Create a **StarRocks** connection" in readme and "set only `idTokenFile`" in readme
