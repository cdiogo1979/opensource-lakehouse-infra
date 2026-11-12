# PR request — Stop and start the scheduled reconciler with the stack

## Problem
`lakehouse.sh stop` left `polaris-group-reconciler` running, contrary to the operations docs; on its own it failed every cycle against the stopped services. `start` didn't start it either, and when stopped it was killed after Docker's 10-second timeout because its shell (PID 1) ignored SIGTERM.

## Solution
- `stop` stops the reconciler first (when its container exists), then the modules and core.
- `start` starts it again last, after core, the modules and StarRocks, when the product bootstrap has set it up; otherwise it prints a notice.
- `infra/polaris/reconciler/run.sh` traps SIGTERM and SIGINT and sleeps interruptibly, so it exits at once with status 0.
- `docs/reference/operations.md` and contract tests.

## Verification
Operations and Polaris tests 88 passed; live `stop` stopped the reconciler; `docker stop` took 0 s with exit code 0.

## Deployment
None beyond the next `start` (the loop script is mounted).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
