# Functional Design Plan — s3-checkpoints

## Steps
- [x] Read the approved Application Design and the canonical baselines (`lakehouse-product-access.md`, `workload-python-environment.md`, `airflow-workflows.md`)
- [x] Resolve the Application Design open points from the code (below)
- [x] Generate domain-entities.md
- [x] Generate business-rules.md
- [x] Generate business-logic-model.md
- [x] Check against requirements (CR-1), Security Baseline and PBT (partial)

## Open points resolved from the code
| Point | Resolution | Evidence |
|---|---|---|
| Where key creation runs | `bootstrap-default-product.sh` and `create-data-product.sh`, right after `bootstrap-policies.py`; `remove-data-product.sh` removes keys before `bootstrap-buckets.py --remove`. `lakehouse.sh start` and `start-airflow` only check that every product bucket has a staged key | RustFS buckets and policies are bootstrapped only by those scripts |
| Staging permissions | As the Airflow writers: folder 755, files 644 (atomic replace), inside `.runtime/container-mounts/` (700, the host user only) | `scripts/setup/stage-airflow-writers.py` |
| Recreate Airflow or the Hub when keys change | Not needed: keys are bind-mounted by host path when each run container or Jupyter server starts, so new or rotated files apply to the next run or server | `factory.py` (bundle and broker CA mounts), `lakehouse_spawner.py` (broker CA pattern) |

## Questions
None open: every functional choice follows from the approved design (CR-1, D1 to D8) or from existing patterns cited above.

[Answer]: n/a (no questions)
