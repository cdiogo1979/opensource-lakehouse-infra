# Execution Plan — Reconciler and StarRocks Recovery

Stages: Code Generation, Build and Test, Deploy handoff (all approved in advance). Skipped: User Stories, Application Design, Units, Functional Design, NFR, Infrastructure Design (changes inside the existing reconciler and StarRocks components; rules stated in the requirements).

## Canonical Knowledge Impact Inventory
| Path | Action | Reason |
|---|---|---|
| `aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/starrocks-sql-access.md` | UPDATE | Bind-pattern recovery step; the scheduled cycle |
| `aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md` | UPDATE | The scheduled reconciler runs mounted current code; health |
| others | RETAIN | Unaffected |
