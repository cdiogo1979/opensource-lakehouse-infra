# Build and Test Summary — Reconciler and StarRocks Recovery

## Build
`docker compose -f compose.core.yml --profile scheduled-reconciliation up -d --build --no-deps polaris-group-reconciler`: image rebuilt (ENTRYPOINT via `/bin/sh`), container recreated with the five code mounts and the healthcheck. Compose config valid; `bash -n` and `sh -n` pass.

## Code analysis
Flake8 clean on the changed Python files; Bandit B310 in `reconcile-starrocks-users.py` is the existing Keycloak `urlopen` (pre-existing).

## Unit tests
`python3 -m pytest -q tests`: 592 passed, 3 skipped. New `tests/polaris/test_reconciler_recovery.py`: mounts cover every script the cycle runs; the bind-pattern step runs first and success needs every step; `--bind-pattern-only` needs neither Keycloak nor valid product files, and fails without a root login; status lists the reconciler; property P1 runs the real healthcheck expression over generated ages and intervals (healthy exactly within 2 × interval + 60 s; unhealthy without the file).

## Integration (live)
| Check | Result |
|---|---|
| StarRocks user sync dry run before re-enabling | no pending change |
| First cycle after recreate | bind pattern already-set; Polaris group sync succeeded (6 principals); StarRocks user sync succeeded (no change); success file written; product model hash equals the repository's |
| StarRocks FE restart | FE healthy after 16 s; bind pattern empty; restored by the scheduled cycle 289 s after the restart ("missing (FE restart) and is set again"), no manual step |
| Health | container `healthy`; `lakehouse.sh status` shows `reconciler  running (healthy)` |

## Not run
A live unhealthy transition (covered by property P1 over the same expression).
