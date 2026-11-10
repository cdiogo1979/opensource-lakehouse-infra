#!/usr/bin/env python3
"""Manage AI-DLC intent artifact compaction using an explicit manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

STATE_FILE = "aidlc-docs/current/aidlc-state.md"
AUDIT_FILE = "aidlc-docs/current/audit.md"
MARKER_START = "<!-- intent-lifecycle:start -->"
MARKER_END = "<!-- intent-lifecycle:end -->"
PROTECTED = ("aidlc-docs/knowledge", "aidlc-docs/archive", STATE_FILE, AUDIT_FILE)


class CompactionError(Exception):
    """Raised when the manifest or workspace fails safe-compaction checks."""


def _safe_relative(value: str) -> Path:
    """Return a validated workspace-relative path.

    Args:
        value: POSIX-style path from the manifest.

    Returns:
        A relative pathlib path.

    Raises:
        CompactionError: If the path is absolute, empty, or traverses upward.
    """
    pure = PurePosixPath(value)
    if not value or pure.is_absolute() or ".." in pure.parts or "\\" in value:
        raise CompactionError(f"Unsafe manifest path: {value!r}")
    return Path(*pure.parts)


def _inside(root: Path, relative: Path) -> Path:
    """Resolve a workspace path and reject symlinks escaping the workspace.

    Args:
        root: Resolved workspace root.
        relative: Validated relative path.

    Returns:
        The resolved target path.

    Raises:
        CompactionError: If resolution escapes the workspace.
    """
    target = (root / relative).resolve()
    if target != root and root not in target.parents:
        raise CompactionError(f"Path escapes workspace: {relative}")
    return target


def _load_lifecycle(state_text: str) -> tuple[dict[str, Any] | None, str, str]:
    """Read lifecycle JSON between stable markers in aidlc-state.md.

    Args:
        state_text: Full Markdown state document.

    Returns:
        Tuple of lifecycle object, prefix before its markers, and suffix after.
    """
    start = state_text.find(MARKER_START)
    end = state_text.find(MARKER_END)
    if start < 0 or end < start:
        return None, state_text, ""
    body_start = start + len(MARKER_START)
    raw = state_text[body_start:end].strip()
    if raw.startswith("```json"):
        raw = raw[7:].strip()
    if raw.endswith("```"):
        raw = raw[:-3].strip()
    return json.loads(raw), state_text[:start], state_text[end + len(MARKER_END) :]


def _write_lifecycle(root: Path, lifecycle: dict[str, Any]) -> None:
    """Atomically persist machine-readable lifecycle metadata in the state file.

    Args:
        root: Workspace root.
        lifecycle: Lifecycle metadata to persist.
    """
    path = root / STATE_FILE
    text = path.read_text(encoding="utf-8")
    existing, prefix, suffix = _load_lifecycle(text)
    del existing
    if "\n## Intent Lifecycle" in prefix:
        prefix = prefix.rsplit("\n## Intent Lifecycle", 1)[0]
    block = f"{MARKER_START}\n```json\n{json.dumps(lifecycle, indent=2, sort_keys=True)}\n```\n" f"{MARKER_END}"
    updated = f"{prefix.rstrip()}\n\n## Intent Lifecycle\n{block}{suffix}"
    _atomic_write(path, updated.encode("utf-8"))


def _atomic_write(path: Path, data: bytes) -> None:
    """Replace a file atomically within its parent directory.

    Args:
        path: Destination file.
        data: Complete replacement bytes.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _validate_manifest(root: Path, intent_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate required manifest fields and constrain all affected paths.

    Args:
        root: Workspace root.
        intent_id: ID supplied on the command line.
        manifest: Parsed manifest object.

    Returns:
        Manifest enriched with a deterministic content digest.

    Raises:
        CompactionError: For incomplete data, unsafe paths, or protected cleanup.
    """
    if manifest.get("intent_id") != intent_id:
        raise CompactionError("Manifest intent_id does not match command argument")
    verification = manifest.get("verification", {})
    verification_status = verification.get("status")
    if verification_status not in ("passed", "waived"):
        raise CompactionError("Compaction requires verification.status = 'passed' or 'waived'")
    if verification_status == "waived" and verification.get("user_accepted") is not True:
        raise CompactionError("A verification waiver requires verification.user_accepted = true")
    if not verification.get("details"):
        raise CompactionError("Verification details must explain the result or accepted limitation")
    for field in ("name", "objective", "date", "scope", "workstreams", "summary", "canonical_updates", "artifacts", "cleanup_paths", "artifact_inventory_complete"):
        if field not in manifest:
            raise CompactionError(f"Manifest is missing required field: {field}")
    if manifest["artifact_inventory_complete"] is not True:
        raise CompactionError("Manifest must assert artifact_inventory_complete = true")
    if not isinstance(manifest["canonical_updates"], list) or not isinstance(manifest["artifacts"], list) or not isinstance(manifest["cleanup_paths"], list):
        raise CompactionError("canonical_updates, artifacts, and cleanup_paths must be arrays")
    for item in manifest["canonical_updates"]:
        rel = _safe_relative(item["path"])
        _inside(root, rel)
        if not str(rel).startswith("aidlc-docs/knowledge/") or "content" not in item:
            raise CompactionError("Canonical updates must target aidlc-docs/knowledge and include content")
    for value in manifest["artifacts"]:
        rel = _safe_relative(value)
        _inside(root, rel)
        if str(rel).startswith("aidlc-docs/archive/"):
            raise CompactionError("Archive inputs cannot come from the archive tree")
    for value in manifest["cleanup_paths"]:
        rel = _safe_relative(value)
        _inside(root, rel)
        workflow_roots = (
            "aidlc-docs/current/inception",
            "aidlc-docs/current/construction",
            "aidlc-docs/current/deploy",
            "aidlc-docs/current/compaction",
        )
        if not any(str(rel) == base or str(rel).startswith(base + "/") for base in workflow_roots):
            raise CompactionError(f"Cleanup is restricted to aidlc-docs/current workflow paths: {rel}")
        if any(str(rel) == protected or str(rel).startswith(protected + "/") or protected.startswith(str(rel) + "/") for protected in PROTECTED):
            raise CompactionError(f"Manifest cannot remove protected path: {rel}")
    digest_source = json.dumps({key: value for key, value in manifest.items() if key != "_digest"}, sort_keys=True, separators=(",", ":")).encode()
    checked = dict(manifest)
    checked["_digest"] = hashlib.sha256(digest_source).hexdigest()
    return checked


def _summary_text(manifest: dict[str, Any], archive_root: str) -> str:
    """Render the compact, discoverable summary for a completed intent.

    Args:
        manifest: Validated intent manifest.
        archive_root: Relative archive directory.

    Returns:
        Markdown summary text.
    """
    summary = manifest["summary"]
    fields = [
        ("Intent", f"{manifest['name']} (`{manifest['intent_id']}`)"),
        ("Objective", manifest["objective"]),
        ("Date", manifest["date"]),
        ("Scope", manifest["scope"]),
        ("Units / workstreams", ", ".join(manifest["workstreams"])),
        ("Major requirements", summary.get("major_requirements", [])),
        ("Architecture and design decisions", summary.get("design_decisions", [])),
        ("Implementation decisions", summary.get("implementation_decisions", [])),
        ("Deviations", summary.get("deviations", [])),
        ("Verification", manifest["verification"].get("details", "Passed")),
        ("Canonical documents updated", [entry["path"] for entry in manifest["canonical_updates"]]),
        ("Superseded decisions", summary.get("superseded_decisions", [])),
        ("Archived artifacts", [f"{archive_root}/full-artifacts/{p}" for p in manifest["artifacts"]]),
    ]
    lines = [f"# Intent Summary: {manifest['name']}", ""]
    for label, value in fields:
        if isinstance(value, list):
            lines.append(f"## {label}")
            lines.extend(f"- {item}" for item in value)
            if not value:
                lines.append("- None recorded")
        else:
            lines.extend((f"## {label}", str(value)))
        lines.append("")
    lines.extend(("## Archive", f"- Full artifacts and audit snapshot: `{archive_root}/full-artifacts/`", ""))
    return "\n".join(lines)


def _copy_verified(source: Path, destination: Path) -> None:
    """Copy a file or directory and verify the copied tree by content hash.

    Args:
        source: Existing source file/directory.
        destination: New archive destination.

    Raises:
        CompactionError: If source is missing or copied bytes do not match.
    """
    if not source.exists():
        raise CompactionError(f"Manifest artifact does not exist: {source}")
    if source.is_dir():
        shutil.copytree(source, destination, symlinks=False)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    if _tree_hash(source) != _tree_hash(destination):
        raise CompactionError(f"Archive verification failed for {source}")


def _tree_hash(path: Path) -> str:
    """Calculate a stable hash for a file or directory tree.

    Args:
        path: File or directory to hash.

    Returns:
        SHA-256 digest of relative names and file contents.
    """
    digest = hashlib.sha256()
    files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    for file_path in files:
        name = file_path.name if path.is_file() else file_path.relative_to(path).as_posix()
        digest.update(name.encode("utf-8"))
        digest.update(file_path.read_bytes())
    return digest.hexdigest()


def _archive_path(intent_id: str) -> str:
    """Return the stable archive directory for an intent.

    Args:
        intent_id: Stable intent identifier.

    Returns:
        Workspace-relative archive path.
    """
    return f"aidlc-docs/archive/{intent_id}"


def _prepare_archive(root: Path, manifest: dict[str, Any], archive: Path) -> None:
    """Build or verify the full-artifacts archive before active cleanup.

    Args:
        root: Workspace root.
        manifest: Validated intent manifest.
        archive: Stable archive destination.

    Raises:
        CompactionError: If a conflicting archive exists or a copy fails.
    """
    marker = archive / "compaction-manifest.sha256"
    if archive.exists():
        if not marker.is_file() or marker.read_text(encoding="utf-8").strip() != manifest["_digest"]:
            raise CompactionError(f"Archive already exists with different or incomplete content: {archive}")
        return
    staging = archive.with_name(f".{archive.name}.staging")
    if staging.exists():
        shutil.rmtree(staging)
    full = staging / "full-artifacts"
    full.mkdir(parents=True)
    inputs = list(dict.fromkeys(manifest["artifacts"] + [STATE_FILE, AUDIT_FILE]))
    for value in inputs:
        rel = _safe_relative(value)
        _copy_verified(_inside(root, rel), full / rel)
    (staging / "intent-summary.md").write_text(_summary_text(manifest, _archive_path(manifest["intent_id"])), encoding="utf-8")
    (staging / "compaction-manifest.sha256").write_text(manifest["_digest"] + "\n", encoding="utf-8")
    archive.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staging, archive)


def preview(root: Path, intent_id: str, manifest: dict[str, Any]) -> str:
    """Describe the proposed compaction without modifying workspace files.

    Args:
        root: Workspace root.
        intent_id: Stable intent identifier.
        manifest: Parsed manifest.

    Returns:
        Human-readable dry-run report.
    """
    checked = _validate_manifest(root, intent_id, manifest)
    archive_root = _archive_path(intent_id)
    lines = [f"Intent: {intent_id}", "Canonical documents to create/update:"]
    for item in checked["canonical_updates"]:
        action = "update" if (root / item["path"]).exists() else "create"
        lines.append(f"  - {action}: {item['path']}")
    lines.append("Artifacts to archive:")
    lines.extend(f"  - {path}" for path in checked["artifacts"])
    lines.extend((f"  - {STATE_FILE} (state snapshot)", f"  - {AUDIT_FILE} (complete audit snapshot)", "Artifacts to remove from active workflow surface:"))
    lines.extend(f"  - {path}" for path in checked["cleanup_paths"])
    lines.extend(("Audit/history retained:", f"  - full audit: {archive_root}/full-artifacts/{AUDIT_FILE}", f"  - active pointer: {AUDIT_FILE}", f"Intent summary: {archive_root}/intent-summary.md"))
    return "\n".join(lines)


def compact(root: Path, intent_id: str, manifest: dict[str, Any], dry_run: bool = False) -> str:
    """Apply or preview a safe, retryable and idempotent intent compaction.

    Args:
        root: Workspace root.
        intent_id: Stable intent identifier.
        manifest: Parsed compaction manifest.
        dry_run: If true, do not write any files.

    Returns:
        Dry-run report or a concise success message.

    Raises:
        CompactionError: If preconditions fail or compaction cannot finish.
    """
    root = root.resolve()
    manifest = _validate_manifest(root, intent_id, manifest)
    state_path = root / STATE_FILE
    lifecycle, _, _ = _load_lifecycle(state_path.read_text(encoding="utf-8"))
    if lifecycle is None or lifecycle.get("intent_id") != intent_id:
        raise CompactionError("State lifecycle intent_id does not match; legacy state remains unchanged")
    status = lifecycle.get("status")
    allowed_statuses = ("VERIFICATION_COMPLETE", "VERIFICATION_WAIVED", "COMPACTION", "COMPACTION_FAILED", "CLOSED")
    if status not in allowed_statuses:
        raise CompactionError(f"Intent must be verification-complete or verification-waived before compaction (current status: {status})")
    is_waived = status == "VERIFICATION_WAIVED" or lifecycle.get("verification_outcome") == "waived"
    if is_waived and lifecycle.get("verification_waiver", {}).get("accepted_by_user") is not True:
        raise CompactionError("Lifecycle waiver requires verification_waiver.accepted_by_user = true")
    expected_manifest_status = "waived" if is_waived else "passed"
    if status in ("VERIFICATION_COMPLETE", "VERIFICATION_WAIVED") and manifest["verification"]["status"] != expected_manifest_status:
        raise CompactionError("Manifest verification status does not match the lifecycle outcome")
    report = preview(root, intent_id, manifest)
    if dry_run:
        return report
    if status == "CLOSED":
        archive = root / _archive_path(intent_id)
        marker = archive / "compaction-manifest.sha256"
        if marker.is_file() and marker.read_text(encoding="utf-8").strip() == manifest["_digest"]:
            return f"Intent {intent_id} is already CLOSED; no changes made."
        raise CompactionError("Intent is CLOSED with a different manifest")
    if status == "CLOSED":
        raise CompactionError("Intent is CLOSED with a different manifest")
    lifecycle["status"] = "COMPACTION"
    _write_lifecycle(root, lifecycle)
    archive = root / _archive_path(intent_id)
    try:
        _prepare_archive(root, manifest, archive)
        for item in manifest["canonical_updates"]:
            destination = _inside(root, _safe_relative(item["path"]))
            _atomic_write(destination, item["content"].encode("utf-8"))
        pointer = (
            f"# Audit Archive Pointer\n\nThe complete audit history through intent `{intent_id}` is preserved at "
            f"`{_archive_path(intent_id)}/full-artifacts/{AUDIT_FILE}`.\n\n"
            f"## Intent Closure: {intent_id}\n**Archive**: `{_archive_path(intent_id)}`\n"
            f"**Summary**: `{_archive_path(intent_id)}/intent-summary.md`\n"
        )
        _atomic_write(root / AUDIT_FILE, pointer.encode("utf-8"))
        for value in manifest["cleanup_paths"]:
            path = _inside(root, _safe_relative(value))
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        lifecycle["status"] = "COMPACTED"
        lifecycle["archive"] = _archive_path(intent_id)
        lifecycle["summary"] = f"{_archive_path(intent_id)}/intent-summary.md"
        _write_lifecycle(root, lifecycle)
        lifecycle["status"] = "CLOSED"
        _write_lifecycle(root, lifecycle)
    except Exception as exc:
        lifecycle["status"] = "COMPACTION_FAILED"
        lifecycle["failure"] = str(exc)
        _write_lifecycle(root, lifecycle)
        if isinstance(exc, CompactionError):
            raise
        raise CompactionError(f"Compaction failed and is retryable: {exc}") from exc
    return f"Intent {intent_id} compacted and CLOSED. Archive: {_archive_path(intent_id)}"


def load_manifest(path: Path) -> dict[str, Any]:
    """Load a JSON manifest from disk.

    Args:
        path: Manifest JSON file.

    Returns:
        Parsed manifest.
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CompactionError(f"Unable to load manifest {path}: {exc}") from exc


def active_context_paths(root: Path) -> list[str]:
    """Select default AI context paths without enumerating archived history.

    Args:
        root: Workspace root.

    Returns:
        Existing canonical knowledge, state, and active workflow document paths.
    """
    selected = [STATE_FILE]
    knowledge = root / "aidlc-docs/knowledge"
    if knowledge.exists():
        selected.extend(p.relative_to(root).as_posix() for p in sorted(knowledge.rglob("*.md")) if p.is_file())
    audit = root / "aidlc-docs/current/audit.md"
    if audit.exists():
        selected.append(audit.relative_to(root).as_posix())
    for area in ("aidlc-docs/current/inception", "aidlc-docs/current/construction", "aidlc-docs/current/deploy"):
        path = root / area
        if path.exists():
            selected.extend(p.relative_to(root).as_posix() for p in sorted(path.rglob("*.md")) if p.is_file())
    manifests = root / "aidlc-docs/current/compaction"
    if manifests.exists():
        selected.extend(p.relative_to(root).as_posix() for p in sorted(manifests.rglob("manifest.json")) if p.is_file())
    return selected


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface.

    Args:
        argv: Optional command-line argument list.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("compact", help="Preview or apply intent artifact compaction")
    command.add_argument("intent_id")
    mode = command.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    command.add_argument("--root", type=Path, default=Path.cwd())
    command.add_argument("--manifest", type=Path)
    args = parser.parse_args(argv)
    manifest_path = args.manifest or args.root / "aidlc-docs/current/compaction" / args.intent_id / "manifest.json"
    try:
        result = compact(args.root, args.intent_id, load_manifest(manifest_path), dry_run=args.dry_run)
        print(result)
        return 0
    except CompactionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
