# Integration Test Instructions (live)

Run in this order against the running stack. Each step lists its expected result.

1. **Baseline**: `python3 scripts/verify/role-matrix.py`. All four `default` roles match.
2. **Migrate** `default` (see the build instructions). A second `--dry-run` plans no Polaris adds or revokes.
3. **After the migration**: `role-matrix.py` gives the same result as the baseline. `polaris-keycloak-auth.py` passes. In StarRocks, `joe-developer` sees only `default_lhdev` in dev, and `peter-analyst` reads production.
4. **Apps** (inside the containers):
   - JupyterHub `lakehouse_policy.approved_groups()` returns the product groups.
   - Airflow `roles_for_groups()` follows the files.
   - Jenkins applies the rendered matrix.
5. **New product**: `create-data-product.sh --init sales`, then a dry run, then apply.
6. **Role matrix for `sales`**: `role-matrix.py --product sales`. Smoke tables are created in `bucket-sales*`, every role matches, and every role is refused in `default`'s namespaces. The reverse holds with `role-matrix.py`.
7. **Users**:
   - `create-user.sh bt-anna`. A duplicate exits 1, and a non-admin `--admin-user` exits 1.
   - Add `bt-anna` to `role-sales-analyst` and run the syncs.
   - Within five minutes (catalog token renewal), `bt-anna` reads `sales` production in StarRocks and is refused `sales` UAT and `default`.
8. **Edit and reapply** `sales` (analyst UAT read, writer prod read). Grants are added and revoked to match, and `role-matrix.py --product sales` matches the edited file.
9. **Remove**:
   - Without `--purge-data`, it refuses, listing data and members, and nothing changes.
   - With `--purge-data --yes`, everything is removed. An interrupted run resumes with the same command.
   - No `sales` objects remain in any system, and `default`'s role matrix still passes.
10. **Sign-in verifiers**:
    - `jenkins-oidc.py` passes all checks except the known missing workload CI job.
    - `rustfs-oidc.py` passes.
    - `polaris-oidc-negative-cases.py` passes.
