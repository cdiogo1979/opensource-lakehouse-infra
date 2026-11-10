# Integration and End-to-End Test Instructions

Run against the live local stack after the build steps.

1. **Reset inventory.** Run `scripts/lakehouse.sh reset --dry-run`. Expect only `lakehouse-local` containers, the 6 data volumes plus `lakehouse-jupyter-home-*`, 6 networks, and 3 `.runtime` directories.
2. **Users.** For each bootstrap user, get a password-grant token from `lakehouse-writer` with `ChangeM3!`. Expect HTTP 200, exactly the listed group, no required actions, a non-temporary credential, and the matching Polaris role. `platform-admin` gets `role-default-owner`.
3. **Re-enforcement.** Change a user's password and groups and add a required action. Run `scripts/bootstrap-users.sh`. Expect the defaults restored and a user outside the list unchanged.
4. **Verifiers.**
   - `scripts/verify-rustfs-oidc.py`
   - `scripts/verify-rustfs-sts.py`
   - `scripts/verify-jenkins-oidc.py`
   - `scripts/verify-polaris-oidc-negative-cases.py`
   - `scripts/verify-role-matrix.py`

   `scripts/verify-polaris-keycloak-auth.py` runs inside the product bootstrap.
5. **Airflow.** Run `scripts/lakehouse.sh start-airflow`. From the scheduler, register a run with the broker and renew it. Expect `preferred_username=srv-default-writer`, `azp=lakehouse-writer`, the writer role, and a 3600 s lifetime.
