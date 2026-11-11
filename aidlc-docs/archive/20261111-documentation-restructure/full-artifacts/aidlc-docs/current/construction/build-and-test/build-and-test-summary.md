# Build and Test Summary — Documentation Restructure

## Coverage of the current README (FR-7)
| Current README section | New place |
|---|---|
| Intro, Components table | `README.draft.md` (intro, Components); roles and connections in `docs-draft/components.md` |
| Quick start | `README.draft.md` Quick start; step details in `journeys/platform-admin.md` §1 |
| Compose modules | `components.md` — Compose modules |
| Users and sign-in (bootstrap users, groups table, where to sign in, restoring defaults, writer password, group changes, LDAP migration) | `reference/identity.md` |
| Data layout | `components.md` — Data layout |
| Data products (file, `repo` block, levels, isolation, Airflow and Jenkins rules) | `components.md` — Data products, Access levels |
| Create or change, Remove a product | `journeys/platform-admin.md` §3 |
| Adding users | `journeys/platform-admin.md` §4 |
| Services: Keycloak | `reference/identity.md` — Keycloak |
| Services: Polaris, RustFS, JupyterHub, Airflow, StarRocks, Jenkins | `reference/polaris.md`, `rustfs.md`, `jupyterhub.md`, `airflow.md`, `starrocks.md`, `jenkins.md` |
| Workload Python environment | `reference/workload-python.md` |
| Streaming checkpoints | `reference/streaming-checkpoints.md` |
| Operations (status, reset, backup, secrets, bootstrap steps) | `reference/operations.md` |
| Scripts | `reference/scripts.md` |
| Known limitations | `reference/limitations.md` (all 13, plus 6 new) and a README summary |

New: architecture and journey diagrams, `security.md`, `evolution.md`, `future-work.md`, the four journey pages, the README index and Start here.

## Automated checks
- **Commands**: 88 code lines of the current README; 87 appear unchanged; 1 changed on purpose (the `status` comment now mentions the reconciler).
- **Code terms**: 371 inline code terms; 370 appear; 1 corrected on purpose (`notebooks/workload/sample/generate_tpch.py` is now `notebooks/workload/sample/other/generate_tpch.py`, its real location).
- **Limitations**: 13 of 13 present.
- **URLs**: 15 of 15 present.
- **Links**: `python3 scripts/verify/docs-links.py README.draft.md docs-draft`: 21 files, no broken links (negative case verified).
- **Tests**: `python3 -m pytest -q tests`: 592 passed, 3 skipped (no code changed).
- **Navigation (NFR-1)**: every page has an audience line and a link back to the README; every page is linked from the README index.

## Not verified
- **Mermaid rendering**: the six diagrams (architecture, security, four journeys) were reviewed by hand; the Mermaid CLI image was blocked by the permission check. To be checked by rendering on GitHub after the switch, or with the CLI if allowed.
