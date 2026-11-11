# Requirements — Data Products Reference Page

Depth: minimal (documentation only, clear request).

## Request
"create a small intent to adjust the docymenttaion once again . Move the data products / Data lyout out of the compoenents reference but to its own reference page . mention that the aidlc is an adpation of the aws v1 aidlc"

## Functional requirements
- **FR-1** New reference page `docs/reference/data-products.md` holding, unchanged in substance, the sections now in `docs/components.md`: Data layout; Data products (the definition file, the `repo` block); Access levels; Materialized views and query acceleration. It opens with the definition and links back to the README definition.
- **FR-2** `docs/components.md` keeps only the component material (how the parts fit together, Compose modules) and a short pointer to the new page.
- **FR-3** Every link into the moved sections (README, journeys, security, Polaris and StarRocks reference pages) points to the new page; the README documentation map lists it.
- **FR-4** AI-DLC is described as an adaptation of AWS's AI-DLC workflows, version 1 ([awslabs/aidlc-workflows](https://github.com/awslabs/aidlc-workflows)), in `docs/reference/aidlc.md`, `docs/evolution.md` and the README component row. What this repository adds is named only where the repository shows it: intent closure (`scripts/aidlc_intent.py compact`) with canonical knowledge and archive under `aidlc-docs/current/`, `knowledge/` and `archive/`, and the always-on Workflow Conventions extension.

## Non-functional
- **NFR-1** No broken relative links or anchors (`scripts/verify/docs-links.py`); pytest unchanged.
- **NFR-2** No content dropped: every line moved from `docs/components.md` appears in the new page.

## Extensions
Security Baseline, Property-Based Testing, Resiliency: not enabled (documentation only).
