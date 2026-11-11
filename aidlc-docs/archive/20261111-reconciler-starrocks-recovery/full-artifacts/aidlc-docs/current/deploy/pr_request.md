# PR request — Scheduled reconciler: current code, StarRocks login recovery, health

## Problem
After a StarRocks FE restart, password logins failed ("empty password is not allowed for simple authentication") for much longer than the documented five minutes. The scheduled reconciler had refused every cycle (`default.yaml has unknown keys: repo`) because its image baked in a 2026-11-09 copy of the product model and scripts, so neither the Polaris group sync nor the StarRocks user sync (which re-applies the bind pattern) ran, and nothing reported it.

## Solution
- The reconciler mounts the repository's `data_products.py`, both reconcile scripts, `starrocks_common.py` and `run.sh` read-only; the image keeps only the runtime.
- Each cycle first runs `reconcile-starrocks-users.py --bind-pattern-only`, which needs only the root login, so logins recover within one interval even if the other syncs are refused.
- A healthcheck marks the container unhealthy after two intervals plus a minute without a fully successful cycle; `lakehouse.sh status` lists it.

## Main changes
`infra/starrocks/reconcile-starrocks-users.py`, `infra/polaris/reconciler/run.sh`, `infra/polaris/reconciler/Dockerfile`, `compose.core.yml`, `scripts/lakehouse.sh`, `README.md`, `tests/polaris/test_reconciler_recovery.py`, `tests/starrocks/test_starrocks_bootstrap_contract.py`.

## Verification
592 passed, 3 skipped; live: first cycle fully successful; after an FE restart the scheduled cycle restored the bind pattern in 289 s; the container reports healthy. Not run live: the unhealthy transition (property-tested).

## Deployment
[deploy_instructions.md](deploy_instructions.md).

## Risks and limitations
- A change to `run.sh` takes effect at the next container start (the loop reads it once); the Python files apply at the next cycle.
- Recovery takes up to one interval (default 300 s); `--bind-pattern-only` on the host fixes it at once.
