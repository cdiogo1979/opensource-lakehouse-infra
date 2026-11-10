# Functional Design Plan — workload-python

## Steps
- [x] Read the unit context: requirements (FR-1 to FR-8, CR-1, CR-2), application design, canonical `airflow-workflows.md`
- [x] Probes for open rule details (TPC-H counts at 0.37, 0.05, 0.001; dry-run resolution as the Jupyter user)
- [x] domain-entities.md
- [x] business-rules.md
- [x] business-logic-model.md, with property identification (PBT-01; PBT-02, 03, 07, 08, 09 enforced)

## Questions
Asked interactively on 2026-11-10.

### Q1 `lakehouse-install-requirements`: packages installed earlier
A) Add, with `--reset`: each run adds; `--reset` empties the folder first; a lock change since the last install requires `--reset` (Recommended)

B) Replace each time

X) Other

[Answer]: A

### Q2 `install_requirements` retries
A) 2 retries, 30 seconds apart (Recommended)

B) No retries

X) Other

[Answer]: A
