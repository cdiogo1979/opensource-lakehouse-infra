"""Decision and safety contracts for the one-time Jenkins home migration."""

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("migrate_jenkins_home", ROOT / "scripts/migrate-jenkins-home.py")
migrate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(migrate)


@pytest.mark.parametrize(
    ("entries", "marker", "legacy_volume", "legacy_running", "action"),
    [
        (12, "migrated:iceberg-poc-jenkins-home 2026-10-31T00:00:00Z", True, False, "skip"),
        (3, "fresh 2026-10-31T00:00:00Z", False, False, "skip"),
        (5, "", True, False, "refuse-unmarked"),
        (5, "", False, False, "refuse-unmarked"),
        (0, "", True, True, "refuse-legacy-running"),
        (0, "", True, False, "copy"),
        (0, "", False, False, "fresh"),
        (0, "", False, True, "fresh"),
    ],
)
def test_decision_table(entries, marker, legacy_volume, legacy_running, action):
    assert migrate.decide(entries, marker, legacy_volume, legacy_running) == action


def test_a_marked_home_is_never_copied_over_even_when_legacy_exists():
    assert migrate.decide(0, "fresh 2026-10-31T00:00:00Z", True, False) == "skip"


def test_names_target_the_approved_volumes_only():
    assert migrate.TARGET_VOLUME == "lakehouse-local_jenkins-home"
    assert migrate.LEGACY_VOLUME == "iceberg-poc-jenkins-home"
    assert migrate.LEGACY_CONTAINER == "hive-dremio-rustfs-jenkins-1"
    assert migrate.IMAGE == "local/lakehouse-jenkins:2.580.1"


def test_copy_reads_the_legacy_volume_read_only_and_marks_last():
    source = (ROOT / "scripts/migrate-jenkins-home.py").read_text(encoding="utf-8")
    assert 'f"{LEGACY_VOLUME}:/src:ro"' in source
    script = migrate.COPY_SCRIPT
    assert script.index("cp -a /src/. /dst/") < script.index("sha256sum") < script.index("> /dst/.lakehouse-home-origin")
    assert "Copied Jenkins home does not match" in script
    assert "set -eu" in script


def test_fresh_home_is_marked_and_owned_by_jenkins():
    assert "fresh %s" in migrate.FRESH_SCRIPT
    assert "chown 1000:1000 /dst" in migrate.FRESH_SCRIPT
