"""The FreeIPA-era RustFS identity scripts stay retired."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RETIRED = (
    "infra/identity-provisioner/reconcile-rustfs-roles.py",
    "infra/identity-provisioner/provision-rustfs-identities.py",
    "infra/identity-provisioner/rustfs-role-policy.json",
)
SKIPPED_DIRECTORIES = {"aidlc-docs", ".agents", ".claude", ".runtime", ".git", ".pytest_cache", ".hypothesis", "__pycache__"}


def test_retired_files_are_absent():
    for path in RETIRED:
        assert not (ROOT / path).exists(), path


def test_no_repository_file_references_the_retired_files():
    names = [Path(path).name for path in RETIRED] + ["provision-rustfs-identities", "reconcile-rustfs-roles"]
    this_file = Path(__file__).resolve()
    offenders = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.resolve() == this_file:
            continue
        if SKIPPED_DIRECTORIES & set(path.relative_to(ROOT).parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if any(name in text for name in names):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
