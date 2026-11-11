# Deployment Instructions — scheduled reconciler

| # | Action | Execution | Validation | Failure handling |
|---|---|---|---|---|
| 1 | Rebuild and recreate the reconciler | `docker compose -f compose.core.yml --profile scheduled-reconciliation up -d --build --no-deps polaris-group-reconciler` (also run by `scripts/bootstrap-default-product.sh`) | `docker logs lakehouse-local-polaris-group-reconciler-1` shows the bind-pattern line and both syncs succeeding | A refusal names its cause (product files, Keycloak, roles); fix it, the next cycle retries |
| 2 | Check health | `./scripts/lakehouse.sh status` | `reconciler  running (healthy)` after up to 3 minutes | `unhealthy`: read the container log |

Already done on this machine. Rollback: revert the files and run step 1 (the old image copies return).
