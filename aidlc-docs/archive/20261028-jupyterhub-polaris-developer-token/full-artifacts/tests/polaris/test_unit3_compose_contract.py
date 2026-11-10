"""Source contract checks for Polaris's local-only management boundary."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_polaris_rest_is_loopback_published_management_is_not_published():
    compose = (ROOT / "docker-compose.yml").read_text()
    polaris = compose.split("  polaris:\n", 1)[1].split("\n  rustfs:\n", 1)[0]
    assert "127.0.0.1:${POLARIS_HOST_PORT:-8181}:8181" in polaris
    assert "8182:" not in polaris
    assert "http://127.0.0.1:8182/q/health/ready" in polaris


def test_polaris_config_is_read_only_on_core_and_data_access_networks():
    compose = (ROOT / "docker-compose.yml").read_text()
    polaris = compose.split("  polaris:\n", 1)[1].split("\n  rustfs:\n", 1)[0]
    assert "polaris-application.properties:/deployment/config/application.properties:ro" in polaris
    assert "networks: [core, data-access]" in polaris
