# Execution Plan — Data Products Reference Page

| Stage | Decision | Reason |
|---|---|---|
| Reverse Engineering | Skip | Documentation analysed in the previous intent |
| User Stories, Application Design, Units | Skip | No new components; one documentation unit |
| Functional / NFR / Infrastructure Design | Skip | No logic or infrastructure |
| Code Generation | Execute | Move sections, rewrite links, AI-DLC origin |
| Build and Test | Execute | Link check, moved-content check, pytest |
| Deploy | Execute | PR description; no deployment |

## Steps
1. Create `docs/reference/data-products.md` from the `docs/components.md` sections (FR-1).
2. Trim `docs/components.md` to components plus a pointer (FR-2).
3. Rewrite links to `components.md#data-products`, `#data-layout`, `#access-levels`, `#materialized-views-and-query-acceleration` (FR-3); add the page to the README map and reference list.
4. AI-DLC origin in `docs/reference/aidlc.md`, `docs/evolution.md`, README (FR-4).
5. Verify (NFR-1, NFR-2).

## Canonical knowledge impact
| Path | Class | Reason |
|---|---|---|
| `aidlc-docs/knowledge/opensource-lakehouse-infra/application-design.md` | UPDATE | "Operational entry points" names the documentation layout; add the data products reference page |
| `functional-design/*.md` | RETAIN | No component behavior changes |
