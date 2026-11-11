# PR request — Data products reference page; AI-DLC origin

## Problem
`docs/components.md` mixed the components with the data layout, the product file, access levels and materialized views, and the documentation did not say where AI-DLC comes from.

## Solution
- **`docs/reference/data-products.md`** (new): data layout, the data product file, access levels, materialized views and query acceleration, moved from `docs/components.md` unchanged in substance.
- **`docs/components.md`**: the components and Compose modules, with a pointer to the new page.
- Links in the README, security page, journeys, Polaris and StarRocks pages point to the new page; the README lists it.
- **AI-DLC**: described as an adaptation of AWS's AI-DLC workflows, version 1 ([awslabs/aidlc-workflows](https://github.com/awslabs/aidlc-workflows)), with the additions in the copy used here (intent closure into canonical knowledge and an archive, the Workflow Conventions extension); most of this adaptation was not written by the platform's author, and its source can no longer be identified.

## Verification
Link check 23 files clean; all 84 moved lines present; pytest 592 passed, 3 skipped.

## Deployment
None: documentation only.

## Risks and limitations
Links from outside this repository to `docs/components.md#data-products`, `#data-layout`, `#access-levels` or `#materialized-views-and-query-acceleration` no longer resolve.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
