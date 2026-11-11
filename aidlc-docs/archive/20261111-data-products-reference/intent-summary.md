# Intent Summary: Data Products Reference

## Intent
Data Products Reference (`20261111-data-products-reference`)

## Objective
Move the data products and data layout content out of docs/components.md into its own reference page, and state that AI-DLC is an adaptation of the AWS AI-DLC v1 workflow.

## Date
2026-11-11

## Scope
Included: docs/reference/data-products.md, docs/components.md, links in README, security, journeys, Polaris and StarRocks pages, AI-DLC origin in docs/reference/aidlc.md, docs/evolution.md and README. Excluded: content changes to the moved sections.

## Units / workstreams
documentation

## Major requirements
- FR-1/FR-2: data layout, product file, access levels and materialized views on docs/reference/data-products.md; docs/components.md keeps the components and Compose modules.
- FR-3: links into the moved sections repointed; the README lists the page.
- FR-4 and CR: AI-DLC is an adaptation of AWS's AI-DLC workflows v1; most of the adaptation was not written by the platform's author and its source can no longer be identified.

## Architecture and design decisions
- Name only the additions the repository shows (intent closure, knowledge and archive layout, Workflow Conventions); no claims about other differences from upstream.

## Implementation decisions
- Relative links in the moved text rebased from docs/ to docs/reference/; Access levels and Materialized views promoted to top-level sections.

## Deviations
- Requirements and workflow planning presented and approved together; code generation, build and test, and deploy presented together.

## Verification
construction/build-and-test/build-and-test-summary.md: docs-links.py 23 files, no broken links; 84 moved lines, 0 missing; pytest 592 passed, 3 skipped. Not checked: the external awslabs/aidlc-workflows link.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md

## Superseded decisions
- docs/components.md as the home of the data layout, product file, access levels and materialized views.

## Archived artifacts
- aidlc-docs/archive/20261111-data-products-reference/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261111-data-products-reference/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261111-data-products-reference/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261111-data-products-reference/full-artifacts/README.md
- aidlc-docs/archive/20261111-data-products-reference/full-artifacts/docs/components.md
- aidlc-docs/archive/20261111-data-products-reference/full-artifacts/docs/reference/data-products.md
- aidlc-docs/archive/20261111-data-products-reference/full-artifacts/docs/reference/aidlc.md
- aidlc-docs/archive/20261111-data-products-reference/full-artifacts/docs/evolution.md
- aidlc-docs/archive/20261111-data-products-reference/full-artifacts/docs/security.md
- aidlc-docs/archive/20261111-data-products-reference/full-artifacts/docs/journeys
- aidlc-docs/archive/20261111-data-products-reference/full-artifacts/docs/reference/polaris.md
- aidlc-docs/archive/20261111-data-products-reference/full-artifacts/docs/reference/starrocks.md
- aidlc-docs/archive/20261111-data-products-reference/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261111-data-products-reference/full-artifacts/`
