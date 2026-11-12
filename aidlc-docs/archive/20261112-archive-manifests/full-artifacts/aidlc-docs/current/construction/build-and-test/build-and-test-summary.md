# Build and Test Summary — Archived Manifests Hidden from Dependabot

| Check | Result |
|---|---|
| `tests/operations/test_aidlc_archive_manifests.py` | 14 passed (the rule, the migration, a full compaction producing `.archived`) |
| Host pytest | 649 passed, 3 skipped |
| Migration | 29 archived manifests renamed (git: 29 renames); a second dry run finds 0 |
| Docs links | 24 files, no broken links |

To check after the push: the dependency graph no longer lists the archived manifests, and their Dependabot alerts close.
