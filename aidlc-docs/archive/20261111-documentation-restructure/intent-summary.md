# Intent Summary: Documentation Restructure

## Intent
Documentation Restructure (`20261111-documentation-restructure`)

## Objective
Make the documentation easy to navigate: clear components, one journey per role, the data product definition, security, platform evolution, known limitations and future work, with a reviewed README draft before replacing the old one.

## Date
2026-11-11

## Scope
Included: README.md rewrite (switched in after review), docs/components.md, docs/journeys/ (4 roles), docs/reference/ (13 pages incl. AI-DLC), docs/security.md, docs/evolution.md, docs/future-work.md, scripts/verify/docs-links.py, a StarRocks docs contract test update, and renaming the canonical knowledge folder from opensource-lakehouse-infra-v2. Excluded: platform behavior changes; integrating materialized-view authoring (follow-up intent).

## Units / workstreams
documentation

## Major requirements
- Components, user journeys for platform-admin, dp-owner, dp-developer and data analyst / BI user, and platform evolution (AI-DLC first, then the big-picture intents).
- A separate README draft reviewed before replacing the old one.
- CR: layered architecture diagram plus one diagram per journey; a security section; an index; known limitations incl. arm64 pins; future work (OpenMetadata, observability, Kubernetes autoscaling); AI-DLC as a component; the data product definition; README order Objective, Architecture, Components, Quick start, Data products, User journeys, Security, then the rest.
- CR-1/CR-2: materialized views available to everyone with query rewrite, authoring in the developer journey; the developer journey points at the sample data product repository.

## Architecture and design decisions
- README as a short landing page; depth in docs/components.md, docs/journeys/ and docs/reference/.
- Every Mermaid diagram has a text version.
- Nothing from the old README dropped: a coverage check against the previous README before the switch.

## Implementation decisions
- scripts/verify/docs-links.py: read-only check of relative links and GitHub anchors, skipping code fences.
- tests/starrocks/test_starrocks_compose_contract.py reads docs/reference/starrocks.md instead of the README.
- Canonical knowledge folder renamed to aidlc-docs/knowledge/opensource-lakehouse-infra/.

## Deviations
- Mermaid CLI validation not run (permission denied); diagrams reviewed by hand.
- Two deliberate coverage differences: the status comment, and the corrected generate_tpch.py path.

## Verification
construction/build-and-test/build-and-test-summary.md: coverage of the old README - commands 87/88, code terms 370/371, limitations 13/13, URLs 15/15 (the two differences deliberate); docs-links.py 22 files, no broken links; pytest 592 passed, 3 skipped. Not verified: Mermaid rendering on GitHub (CLI renderer denied; reviewed by hand).

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md

## Superseded decisions
- The single long README with every service's operation, superseded by the landing page plus docs/ tree.
- The canonical folder name opensource-lakehouse-infra-v2, superseded by opensource-lakehouse-infra.

## Archived artifacts
- aidlc-docs/archive/20261111-documentation-restructure/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261111-documentation-restructure/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261111-documentation-restructure/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261111-documentation-restructure/full-artifacts/README.md
- aidlc-docs/archive/20261111-documentation-restructure/full-artifacts/docs
- aidlc-docs/archive/20261111-documentation-restructure/full-artifacts/scripts/verify/docs-links.py
- aidlc-docs/archive/20261111-documentation-restructure/full-artifacts/tests/starrocks/test_starrocks_compose_contract.py
- aidlc-docs/archive/20261111-documentation-restructure/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261111-documentation-restructure/full-artifacts/`
