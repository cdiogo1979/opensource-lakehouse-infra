"""Compose, runtime-secret, and operator contracts for the v2 Jenkins service."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
LAKEHOUSE = (ROOT / "scripts/lakehouse.sh").read_text(encoding="utf-8")


def jenkins_service() -> str:
    body = COMPOSE.split("\n  jenkins:\n", 1)[1]
    return re.split(r"\n  [a-z][a-z0-9-]*:\n|\nnetworks:\n", body, maxsplit=1)[0]


def test_service_is_loopback_only_without_docker_socket():
    service = jenkins_service()
    assert "127.0.0.1:${JENKINS_HOST_PORT:-8090}:8080" in service
    assert "docker.sock" not in service
    assert "group_add" not in service
    assert "networks: [core]" in service


def test_service_uses_pinned_image_casc_and_secret_mounts():
    service = jenkins_service()
    assert "image: local/lakehouse-jenkins:2.580.1" in service
    assert "context: ./infra/jenkins" in service
    assert "CASC_JENKINS_CONFIG: /var/jenkins_casc/jenkins.yaml" in service
    assert 'PLUGINS_FORCE_UPGRADE: "true"' in service
    assert "JAVA_OPTS: -Djenkins.install.runSetupWizard=false" in service
    assert "- jenkins-home:/var/jenkins_home" in service
    assert "./infra/jenkins/casc/jenkins.yaml:/var/jenkins_casc/jenkins.yaml:ro" in service
    assert "jenkins-oidc-client-secret:/run/secrets/jenkins_oidc_client_secret:ro" in service
    assert "jenkins-break-glass-password:/run/secrets/jenkins_break_glass_password:ro" in service
    assert "condition: service_healthy" in service and "keycloak:" in service
    assert "http://127.0.0.1:8080/login" in service


def test_home_volume_name_and_no_secrets_in_compose():
    assert "  jenkins-home:\n    name: lakehouse-local_jenkins-home" in COMPOSE
    assert "CLIENT_SECRET" not in COMPOSE
    assert not re.search(r"(?i)jenkins[_-]?(admin_)?password\s*:", COMPOSE)


def test_runtime_preparation_creates_and_stages_jenkins_secrets():
    source = (ROOT / "scripts/prepare-lakehouse-runtime.py").read_text(encoding="utf-8")
    assert 'read_or_create("jenkins-oidc-client-secret", secrets.token_hex(32))' in source
    assert 'read_or_create("jenkins-break-glass-password", secrets.token_hex(24))' in source
    staging = source.split('for filename in (\n        "rustfs-access-key",', 1)[1].split("):", 1)[0]
    assert '"jenkins-oidc-client-secret"' in staging and '"jenkins-break-glass-password"' in staging


def test_deferred_inventory_and_env_example():
    deferred = (ROOT / "docker-compose.deferred.yml").read_text(encoding="utf-8")
    assert "  jenkins:\n    status: implemented-in-main-compose" in deferred
    assert "JENKINS_HOST_PORT=8090" in (ROOT / ".env.example").read_text(encoding="utf-8")


def test_core_start_migrates_then_starts_jenkins():
    start = LAKEHOUSE.split("start_stack() {", 1)[1].split("\n}\n", 1)[0]
    order = [start.index(step) for step in (
        "python3 infra/keycloak/bootstrap-realm.py",
        '"${COMPOSE[@]}" build jenkins',
        "python3 scripts/migrate-jenkins-home.py",
        '"${COMPOSE[@]}" up -d jenkins',
        "wait_for_services jenkins",
    )]
    assert order == sorted(order)
    assert "jenkins)" in LAKEHOUSE.split("SERVICES=(", 1)[1].split("\n", 1)[0] + ")"
    assert '"${COMPOSE[@]}" stop jenkins jupyterhub' in LAKEHOUSE


def test_legacy_removal_is_guarded_and_exact():
    body = LAKEHOUSE.split("remove_legacy_jenkins() {", 1)[1].split("\n}\n", 1)[0]
    assert 'legacy_container=hive-dremio-rustfs-jenkins-1 legacy_volume=iceberg-poc-jenkins-home' in body
    assert '"${1:-}" != "--confirm"' in body
    assert '"migrated:${legacy_volume} "*' in body
    assert '"$state" != healthy' in body
    assert 'docker rm "$legacy_container"' in body and 'docker volume rm "$legacy_volume"' in body
    commands = "\n".join(line for line in body.splitlines() if not line.strip().startswith("#"))
    assert "jenkins_home" not in commands.replace("lakehouse-local_jenkins-home", "")
    assert "rmi" not in body and "--force" not in body and " -f " not in body
    assert "remove-legacy-jenkins) remove_legacy_jenkins" in LAKEHOUSE
