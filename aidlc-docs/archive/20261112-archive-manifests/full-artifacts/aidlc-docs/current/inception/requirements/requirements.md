# Requirements — Archived Manifests Hidden from Dependabot

## Request
"lets start with the small intent to change the compactation and rename the archive requirement files so they are not picked by dependabot"

## Context
GitHub's dependency graph reads 29 manifests under `aidlc-docs/archive/` (copies of retired or old `requirements*.txt`, a `pom.xml`, a workflow file); repository auto-triage rules need exact manifest paths (a folder is refused), and each closure that changes a manifest would add more.

## Requirements
- **FR-1** `scripts/aidlc_intent.py compact` renames dependency manifests inside the new archive's `full-artifacts/` to `<name>.archived` (content unchanged), after the verified copy: `requirements*.txt`, `pom.xml`, `pyproject.toml`, `Pipfile`, `Pipfile.lock`, `poetry.lock`, `package.json`, `package-lock.json`, `yarn.lock`, `go.mod`, `go.sum`, `Cargo.toml`, `Cargo.lock`, `Gemfile`, `Gemfile.lock`, `composer.json`, `composer.lock`, and workflow files under `.github/workflows/`.
- **FR-2** A one-time migration renames the same files in the existing archives (git history keeps the rename), with a dry run; the intent summaries and hash markers are unaffected (the marker hashes the manifest JSON, not the files).
- **FR-3** Docs: the vulnerability-alerts page drops the auto-triage rule (no longer needed) and says how archived manifests are stored; the AI-DLC reference mentions it.
- **NFR-1** Tests for the rename rule and for a compaction producing `.archived` names.

## Note
The sample repository has the same `scripts/aidlc_intent.py`; its archives hold no manifests today. Bringing its copy in line is a separate small intent there.
