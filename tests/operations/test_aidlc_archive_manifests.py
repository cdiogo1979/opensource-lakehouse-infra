"""Archived dependency manifests are renamed so GitHub's dependency graph ignores them (archive-manifests FR-1, FR-2)."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("aidlc_intent", ROOT / "scripts/aidlc_intent.py")
aidlc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aidlc)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("infra/airflow/requirements.txt", True),
        ("tests/requirements-pbt.txt", True),
        ("infra/jupyter/hub/requirements-lock.txt", True),
        ("infra/spark-token-provider/pom.xml", True),
        ("x/package-lock.json", True),
        ("x/go.sum", True),
        (".github/workflows/vulnerability-scan.yml", True),
        ("infra/workload-python/requirements.lock", False),  # GitHub doesn't parse it
        ("infra/workload-python/requirements.in", False),
        ("aidlc-docs/current/inception/requirements/requirements.md", False),
        ("docs/workflows/notes.yml", False),
        ("requirements.txt.archived", False),
    ],
)
def test_the_rule_matches_what_the_dependency_graph_reads(path, expected):
    assert aidlc.is_dependency_manifest(Path(path)) is expected


def test_the_migration_renames_manifests_keeps_content_and_is_idempotent(tmp_path):
    archive = tmp_path / "aidlc-docs/archive/x/full-artifacts"
    (archive / "infra/airflow").mkdir(parents=True)
    (archive / "infra/airflow/requirements.txt").write_text("authlib==1.8.0\n")
    (archive / "README.md").write_text("docs")
    assert aidlc.neutralize_manifests(tmp_path / "aidlc-docs/archive", dry_run=True) == [archive / "infra/airflow/requirements.txt"]
    assert (archive / "infra/airflow/requirements.txt").exists()
    aidlc.neutralize_manifests(tmp_path / "aidlc-docs/archive")
    assert (archive / "infra/airflow/requirements.txt.archived").read_text() == "authlib==1.8.0\n"
    assert not (archive / "infra/airflow/requirements.txt").exists() and (archive / "README.md").exists()
    assert aidlc.neutralize_manifests(tmp_path / "aidlc-docs/archive") == []


def test_a_closure_archives_manifests_under_the_archived_name(tmp_path):
    root = tmp_path
    (root / "aidlc-docs/current/compaction/i1").mkdir(parents=True)
    (root / "aidlc-docs/current/inception").mkdir(parents=True)
    (root / "aidlc-docs/current/inception/requirements.md").write_text("r")
    (root / "infra/app").mkdir(parents=True)
    (root / "infra/app/requirements.txt").write_text("requests==2.32.3\n")
    lifecycle = {"intent_id": "i1", "status": "VERIFICATION_COMPLETE", "current_stage": "DEPLOY"}
    (root / aidlc.STATE_FILE).write_text(f"# State\n\n{aidlc.MARKER_START}\n```json\n{json.dumps(lifecycle)}\n```\n{aidlc.MARKER_END}\n")
    (root / aidlc.AUDIT_FILE).write_text("# Audit\n")
    manifest = {
        "intent_id": "i1", "name": "I1", "objective": "o", "date": "2026-11-12", "scope": "s", "workstreams": ["w"],
        "verification": {"status": "passed", "details": "d"}, "artifact_inventory_complete": True,
        "summary": {"major_requirements": [], "design_decisions": [], "implementation_decisions": [], "deviations": [], "superseded_decisions": []},
        "canonical_updates": [], "artifacts": ["aidlc-docs/current/inception", "infra/app/requirements.txt"], "cleanup_paths": ["aidlc-docs/current/inception"],
    }
    path = root / "aidlc-docs/current/compaction/i1/manifest.json"
    path.write_text(json.dumps(manifest))
    aidlc.compact(root, "i1", aidlc.load_manifest(path))
    full = root / "aidlc-docs/archive/i1/full-artifacts"
    assert (full / "infra/app/requirements.txt.archived").read_text() == "requests==2.32.3\n"
    assert not (full / "infra/app/requirements.txt").exists()
    assert (root / "infra/app/requirements.txt").exists()  # the live manifest is untouched
