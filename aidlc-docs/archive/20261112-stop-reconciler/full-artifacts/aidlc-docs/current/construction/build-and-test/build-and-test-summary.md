# Build and Test Summary — Stop and Start the Scheduled Reconciler

| Check | Result |
|---|---|
| `bash -n scripts/lakehouse.sh`, `sh -n infra/polaris/reconciler/run.sh` | OK |
| `tests/operations`, `tests/polaris` | 88 passed (stop order, start after StarRocks, SIGTERM trap) |
| Live: `lakehouse.sh stop` with only the reconciler running | reconciler stopped, nothing left running |
| Live: `docker stop` after the trap | 0 s, exit code 0, "Reconciler stopping" (before: killed after 10 s, exit 137) |

Not run live: `start` (the stack was stopped by the user; the start path is covered by the contract test).
