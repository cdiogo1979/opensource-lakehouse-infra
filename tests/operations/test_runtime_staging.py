"""Staged read-only mounts keep their inode when unchanged (mv-promotion CR-2).

Every lakehouse.sh start re-runs prepare-runtime.py. Replacing an unchanged staged
file gave it a new inode, so containers that weren't recreated (the core reconciler
after start-airflow) kept a deleted file and failed every cycle.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("prepare_runtime", ROOT / "scripts/setup/prepare-runtime.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "CREDENTIALS", tmp_path / "credentials")
    monkeypatch.setattr(module, "CONTAINER_MOUNTS", tmp_path / "mounts")
    (tmp_path / "credentials").mkdir()
    (tmp_path / "mounts").mkdir()
    return module


def test_an_unchanged_mount_keeps_its_inode_and_a_changed_one_is_replaced(tmp_path, monkeypatch):
    module = load(tmp_path, monkeypatch)
    (tmp_path / "credentials/secret").write_text("one")
    module.stage_readonly_mount("secret")
    staged = tmp_path / "mounts/secret"
    first = staged.stat().st_ino
    module.stage_readonly_mount("secret")
    assert staged.stat().st_ino == first and staged.read_text() == "one"
    (tmp_path / "credentials/secret").write_text("two")
    module.stage_readonly_mount("secret")
    assert staged.read_text() == "two" and oct(staged.stat().st_mode & 0o777) == "0o644"
