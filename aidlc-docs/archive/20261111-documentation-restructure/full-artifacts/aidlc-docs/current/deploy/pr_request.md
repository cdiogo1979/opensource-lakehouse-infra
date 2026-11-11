# PR request — Restructure the documentation by component and user journey

## Problem
The README had grown to 589 lines organized by mechanism, so each role had to piece its path together from several sections, there was no overview of how the components fit together, no security overview, and no history of why the platform looks as it does.

## Solution
- **`README.md`**: a short landing page with an index, the core definition **What is a data product**, a layered architecture diagram, the component table, the quick start, a Security summary, "Start here" by role, a map of all pages, Known limitations, and Future work.
- **`docs/components.md`**: how the parts fit together, Compose modules, data layout, data products, access levels, materialized views and query acceleration.
- **`docs/journeys/`**: platform admin, data product owner, data product developer (pointing to the sample data product repository for the repository structure), data analyst and BI user, each with a journey diagram.
- **`docs/reference/`**: the detail per component (identity, Polaris, RustFS, JupyterHub, Airflow, StarRocks, Jenkins, workload Python, streaming checkpoints), operations, scripts, and known limitations (with the arm64 pins).
- **AI-DLC as a component**: a row in the component tables, a node in the architecture diagram, and `docs/reference/aidlc.md` (parts, how a change goes, rules).
- **`docs/security.md`**, **`docs/evolution.md`** (the AI-DLC method and four phases of intents), **`docs/future-work.md`** (OpenMetadata, observability, Kubernetes, identified improvements).
- **`scripts/verify/docs-links.py`**: a read-only link and anchor checker.
- `tests/starrocks/test_starrocks_compose_contract.py` reads the new docs tree.

## Verification
Coverage against the previous README: 87 of 88 command lines unchanged (one comment updated), 370 of 371 code terms (one outdated path corrected), all 13 limitations, all 15 URLs; link check clean (21 files); pytest 592 passed, 3 skipped. Not verified: Mermaid rendering (reviewed by hand; check on GitHub).

## Deployment
None: documentation only. The previous README is archived with the intent.

## Risks and limitations
Links into the old README's anchors from outside this repository (if any) no longer resolve; the six Mermaid diagrams render only where Mermaid is supported (GitHub does).
