# Requirements — Stop and Start the Scheduled Reconciler

## Request
"lakehouse stop command leaves the polaris reconciliar running , is that supposed?" then "yes proceed" (to the fix described).

## Finding
`scripts/lakehouse.sh stop` stops the modules and core services but not `polaris-group-reconciler` (Compose profile `scheduled-reconciliation`, started only by `bootstrap-default-product.sh`), although `docs/reference/operations.md` says `stop` stops what `status` shows, the reconciler included. Left alone it fails every cycle against the stopped services. `start` doesn't start it either.

## Requirements
- **FR-1** `stop` stops the reconciler first, before the services it reads, when its container exists.
- **FR-2** `start` starts it again after core, the modules and StarRocks are up, when its container exists (it was set up by the product bootstrap); otherwise it prints a notice that the bootstrap sets it up.
- **FR-3** `docs/reference/operations.md` says so; a contract test checks both.
