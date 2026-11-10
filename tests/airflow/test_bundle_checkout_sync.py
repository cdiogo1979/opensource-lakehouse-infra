"""Existing bundle checkouts get newly configured sparse directories (sync-bundle-checkouts.py)."""

import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("sync_bundle_checkouts", ROOT / "scripts/setup/sync-bundle-checkouts.py")
sync_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync_module)

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is required")


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "HOME": str(cwd)})


def checkout(tmp_path, dirs):
    """A bundle tracking_repo cloned the way GitDagBundle does: sparse, cone mode."""
    origin = tmp_path / "origin"
    for directory in ("dags", "workflows", "notebooks", "configs", "secret_stuff"):
        (origin / directory).mkdir(parents=True)
        (origin / directory / "f.txt").write_text(directory)
    git(origin, "init", "-q", "-b", "main")
    git(origin, "add", ".")
    git(origin, "commit", "-q", "-m", "init")
    repo = tmp_path / "bundles" / "default-uat" / "tracking_repo"
    git(tmp_path, "clone", "-q", "--sparse", "--no-checkout", str(origin), str(repo))
    git(repo, "sparse-checkout", "init", "--cone")
    git(repo, "sparse-checkout", "set", *dirs)
    git(repo, "checkout", "-q", "main")
    return tmp_path / "bundles", repo


def test_a_missing_directory_is_added_and_a_second_run_changes_nothing(tmp_path):
    root, repo = checkout(tmp_path, ["dags", "configs", "notebooks"])
    assert not (repo / "workflows").exists()
    wanted = ["dags", "workflows", "notebooks", "configs"]
    assert sync_module.sync(root, ["default-uat", "default-main"], wanted, dry_run=True) == ["default-uat"]
    assert not (repo / "workflows").exists()
    assert sync_module.sync(root, ["default-uat", "default-main"], wanted) == ["default-uat"]
    assert (repo / "workflows/f.txt").read_text() == "workflows" and not (repo / "secret_stuff").exists()
    assert sync_module.sync(root, ["default-uat"], wanted) == []


def test_start_airflow_synchronizes_before_starting_airflow():
    script = (ROOT / "scripts/lakehouse.sh").read_text()
    body = script.split("start_airflow() {", 1)[1]
    assert body.index("python3 scripts/setup/sync-bundle-checkouts.py") < body.index('"${AIRFLOW_COMPOSE[@]}" up --build -d')
