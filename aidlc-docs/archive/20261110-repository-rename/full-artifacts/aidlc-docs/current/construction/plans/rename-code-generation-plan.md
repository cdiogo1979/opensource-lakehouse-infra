# Code Generation Plan — rename

## Platform (this workspace)
- [x] **Step 1** — `data-products/default.yaml`: `repo.url` → `https://github.com/cdiogo1979/opensource-lakehouse-sample-dp.git` (FR-2).
- [x] **Step 2** — `README.md`: the product example's `url` and the mentions of `opensource-lakehouse` (FR-3).
- [x] **Step 3** — `tests/jenkins/test_product_pipelines.py`: the expected remote and `repository('opensource-lakehouse-sample-dp')` (FR-3). Fixtures that need any URL stay.

## Workload repository (scratchpad clone, from `42de0f3`)
- [x] **Step 4** — remote URL → the new name (FR-5).
- [x] **Step 5** — the three notebooks' Initialization line, README (clone command, paths), AGENTS.md, `tests/workload_foundation/test_jupyter_scripts.py`: `~/work/opensource-lakehouse-sample-dp` (FR-4); pushed after approval.

## Documentation
- [x] **Step 6** — `construction/rename/code/code-summary.md`.

Knowledge updates (FR-6) are made at closure, through the manifest. The stack recreation is Build and Test.
