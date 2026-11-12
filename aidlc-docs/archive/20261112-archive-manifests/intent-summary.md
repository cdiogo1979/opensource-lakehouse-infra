# Intent Summary: Archived Manifests Hidden from Dependabot

## Intent
Archived Manifests Hidden from Dependabot (`20261112-archive-manifests`)

## Objective
Stop Dependabot alerting on dependency manifests copied into aidlc-docs/archive/.

## Date
2026-11-12

## Scope
Included: aidlc_intent.py (closure rename and neutralize-archives), the one-time migration of 29 files, docs, tests. Excluded: the sample repository's copy of the script (separate intent).

## Units / workstreams
aidlc-tooling

## Major requirements
- FR-1 closure renames archived manifests to <name>.archived.
- FR-2 one-time migration of existing archives.
- FR-3 docs.

## Architecture and design decisions
- Rename instead of a UI auto-triage rule (manifest paths only, no folders; grows with every closure).

## Implementation decisions
- is_dependency_manifest mirrors the names GitHub parses; the archive marker hashes the manifest JSON, so renamed files break no check.

## Deviations
- Existing archives changed (renames only) at the user's request.

## Verification
construction/build-and-test/build-and-test-summary.md: 649 passed, 3 skipped; 29 renames, second dry run 0.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md

## Superseded decisions
- Archive alerts dismissed by a UI auto-triage rule.

## Archived artifacts
- aidlc-docs/archive/20261112-archive-manifests/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261112-archive-manifests/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261112-archive-manifests/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261112-archive-manifests/full-artifacts/scripts/aidlc_intent.py
- aidlc-docs/archive/20261112-archive-manifests/full-artifacts/tests/operations/test_aidlc_archive_manifests.py
- aidlc-docs/archive/20261112-archive-manifests/full-artifacts/docs/reference/vulnerability-alerts.md
- aidlc-docs/archive/20261112-archive-manifests/full-artifacts/docs/reference/aidlc.md
- aidlc-docs/archive/20261112-archive-manifests/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261112-archive-manifests/full-artifacts/`
