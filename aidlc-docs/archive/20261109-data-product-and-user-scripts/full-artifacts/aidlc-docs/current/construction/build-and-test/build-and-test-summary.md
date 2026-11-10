# Build and Test Summary — Data Product and User Scripts

## Outcome: passed, with known items
| Check | Result |
|---|---|
| Contract suite | 332 passed, 1 skipped, 1 known failure (Airflow developer-role drift) |
| `default` migration to namespace-scoped grants | Role matrix identical before and after; Polaris converged (102 added, 64 revoked, then 0/0); StarRocks converged (46 added, 73 revoked) |
| Polaris restart with `ALLOW_NAMESPACE_CUSTOM_LOCATION` and the group pattern | Healthy; settings seen in the container |
| Apps recreated with the product mounts | JupyterHub, Airflow, and Jenkins follow the files; the sync image runs both syncs |
| New product `sales` (init, dry run, apply) | Every component created; role matrix matches; isolation holds both ways |
| New user `bt-anna` | Created with no groups; duplicate and non-admin refused; access follows the group |
| Edit and reapply | Additions and revocations applied; role matrix matches the edited file |
| Removal | Refused with data; purged and removed; resumed after a fix; nothing left behind; `default` intact |
| Sign-in verifiers | Pass, except the known missing Jenkins workload CI job |

## Findings fixed during Build and Test
All seven are listed in `construction/data-product-provisioning/code/code-summary.md`:
- `airflow-init` import of the product model
- the Polaris dry-run binding report
- the non-admin refusal message
- the Polaris and StarRocks syncs during a removal
- role-matrix cleanup after access edits
- test-session isolation from the local product files

## Behaviour to note
- **StarRocks delay**: a new product's tables are readable through StarRocks within about five minutes, when the shared catalogs renew their Polaris token. This is documented in the README.
- **Removal backups**: each removal run writes a backup. Two interrupted runs left three backup directories for `sales` in `.runtime/backups/`.

## Test residue
- **Removed**: the test user `bt-anna` and the `sales` product.
- **Remaining**: `bt-anna`'s Polaris principal, without roles (the existing behaviour for deleted users), and the `sales` removal backups.
