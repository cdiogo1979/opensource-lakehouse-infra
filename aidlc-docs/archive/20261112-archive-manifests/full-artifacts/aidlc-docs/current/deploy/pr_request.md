# PR request — Hide archived dependency manifests from Dependabot

## Problem
GitHub's dependency graph read 29 dependency manifests copied into `aidlc-docs/archive/` by intent closures (retired components and older versions), so Dependabot alerted on software the platform no longer runs. Repository auto-triage rules can't target a folder, and every closure that changed a manifest would add more.

## Solution
- `scripts/aidlc_intent.py compact` renames dependency manifests inside a new archive to `<name>.archived` (content unchanged): `requirements*.txt`, `pom.xml`, `pyproject.toml`, lock files of other ecosystems, and `.github/workflows/*.yml` copies.
- `scripts/aidlc_intent.py neutralize-archives --dry-run|--apply` renames them in existing archives; applied once (29 files, kept as git renames). The archive markers hash the manifest JSON, so they stay valid.
- Docs: the vulnerability-alerts page (no UI rule needed) and the AI-DLC reference.

## Verification
Tests 649 passed, 3 skipped (14 new: the rule, the migration, a full compaction).

## Deployment
Push; GitHub re-reads the repository and closes the archive alerts.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
