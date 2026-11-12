# Execution Plan — Spark Base Image

| Stage | Decision | Reason |
|---|---|---|
| Design stages | Skip | Base swap inside the existing component; differences listed in the requirements |
| Code Generation | Execute | Dockerfiles, tests, docs |
| Build and Test | Execute | Build both images; tests; parity; Trivy; live checks (approval) |
| Deploy | Execute | Commit and push (approval) |

## Canonical knowledge impact
| Path | Class | Reason |
|---|---|---|
| `functional-design/workload-python-environment.md` | UPDATE | Venv base interpreter, image base |
| `application-design.md` | UPDATE | Spark runtime base and version |
