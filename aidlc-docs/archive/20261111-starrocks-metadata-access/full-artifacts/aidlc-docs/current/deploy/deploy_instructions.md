# Deployment Instructions — StarRocks metadata grant

| # | Action and target | Prerequisites | Execution | Validation | Failure handling |
|---|---|---|---|---|---|
| 1 | Apply the grants in StarRocks | StarRocks running and bootstrapped; root password file in `.runtime/credentials/` | `python3 infra/starrocks/bootstrap-starrocks.py` (also part of `scripts/bootstrap-default-product.sh` and the product commands) | "StarRocks roles: ... applied"; a second `--dry-run` reports only the 27 grants it always reissues | A failed run names the step and changes nothing further; rerun after fixing |
| 2 | SQL client users reconnect | Step 1 | Disconnect and reconnect (DBeaver: Disconnect, then Connect) | Tables listed under each catalog's database without error 5203 | Still refused: check the user's roles with `SHOW GRANTS` as root |

Already done on this machine during Build and Test. Rollback: revert the code and rerun step 1; the bootstrap revokes the grant as uncovered.
