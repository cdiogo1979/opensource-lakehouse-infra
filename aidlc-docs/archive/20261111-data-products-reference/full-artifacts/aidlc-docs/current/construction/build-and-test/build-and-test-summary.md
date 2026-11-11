# Build and Test Summary — Data Products Reference Page

| Check | Result |
|---|---|
| `scripts/verify/docs-links.py` (README.md, docs/) | 23 files, no broken links |
| Moved content: every non-empty line of the old `docs/components.md` from "Data layout" on, links normalized, present in the new page | 84 lines, 0 missing |
| `python3 -m pytest -q tests` | 592 passed, 3 skipped |

Not checked: the external link https://github.com/awslabs/aidlc-workflows (the link checker covers relative links only).
