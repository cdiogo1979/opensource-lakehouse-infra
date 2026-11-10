"""The Jenkins image installs exactly the pinned plugin set."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLUGINS = ROOT / "infra/jenkins/plugins.txt"
DOCKERFILE = (ROOT / "infra/jenkins/Dockerfile").read_text(encoding="utf-8")


def pins() -> list[tuple[str, str]]:
    lines = [line for line in PLUGINS.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")]
    return [tuple(line.split(":", 1)) for line in lines]


def test_every_plugin_is_pinned_to_an_exact_version():
    entries = pins()
    assert len(entries) == 105
    for name, version in entries:
        assert re.fullmatch(r"[a-z0-9][a-z0-9._-]*", name), name
        assert version and not any(token in version for token in ("latest", "experimental", "*", " ")), name


def test_plugin_names_are_unique_and_sorted():
    names = [name for name, _ in pins()]
    assert names == sorted(names)
    assert len(names) == len(set(names))


def test_required_plugins_are_present_at_approved_versions():
    versions = dict(pins())
    assert versions["oic-auth"] == "4.731.v4932b_506e767"
    assert versions["nimbus-jose-jwt-api"] == "10.10-12.vd4e6d651b_7f7"
    assert versions["matrix-auth"] == "3.3"
    assert versions["configuration-as-code"] == "2136.veb_3a_554550b_f"
    assert versions["job-dsl"] == "3732.v9a_c49a_61a_313"
    for name in ("workflow-aggregator", "workflow-multibranch", "git", "cloudbees-folder", "github-branch-source"):
        assert name in versions


def test_dockerfile_installs_and_verifies_the_pinned_set():
    assert "COPY --chown=jenkins:jenkins plugins.txt /usr/share/jenkins/ref/plugins.txt" in DOCKERFILE
    assert "jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt" in DOCKERFILE
    assert 'Installed plugins do not match plugins.txt (name:version)' in DOCKERFILE
    # Versions are compared too, so a dependency resolved to another version fails the build.
    assert 'sed -n \'s/^Plugin-Version: //p\'' in DOCKERFILE
    assert "FROM jenkins/jenkins:lts-jdk21@sha256:" in DOCKERFILE
