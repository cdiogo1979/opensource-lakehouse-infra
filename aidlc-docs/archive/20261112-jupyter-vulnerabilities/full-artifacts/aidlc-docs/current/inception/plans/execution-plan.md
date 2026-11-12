# Execution Plan — Jupyter Vulnerabilities

| Stage | Decision | Reason |
|---|---|---|
| Design stages | Skip | Version and pin changes inside existing images |
| Code Generation | Execute | Digests, requirements, residual patches, tests, docs |
| Build and Test | Execute | Rebuild both images; contract tests and parity; Trivy re-scan; live: `start` with the new images, sign-in, spawn, kernel and Spark, Git sidebar, widgets (approval for the restart) |
| Deploy | Execute | Commit and push (approval) |

Steps: 1) digests and pins; 2) rebuild and re-scan; 3) patch the remainder; 4) tests; 5) live check; 6) docs.

## Canonical knowledge impact
| Path | Class | Reason |
|---|---|---|
| `functional-design/lakehouse-product-access.md` or the JupyterHub part of `application-design.md` | UPDATE | Base versions and pins |
| `functional-design/workload-python-environment.md` | RETAIN | Lock unchanged |
