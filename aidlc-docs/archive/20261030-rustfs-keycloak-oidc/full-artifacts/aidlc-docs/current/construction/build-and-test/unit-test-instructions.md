# Unit Test Execution — rustfs-keycloak-oidc

## Run Unit Tests

### 1. Suites for this intent
```bash
python3 -m pytest -q tests/rustfs tests/keycloak tests/polaris --hypothesis-seed=20261030
```
- `tests/rustfs/test_policy_contract.py`: access matrix, absent-policy detection, conflict refusal, Hypothesis properties P1–P5.
- `tests/keycloak/test_rustfs_client_contract.py`: client, mapper, port resolution, reconciliation, and refusals.
- `tests/rustfs/test_compose_oidc_contract.py`: Compose/network contracts and behavioral wrapper tests.
- `tests/rustfs/test_legacy_retirement.py`: retired files absent and unreferenced.

### 2. Full suite (as CI)
```bash
PYTHONPATH=infra/jupyter/hub python3 -m pytest -q tests --hypothesis-seed=<seed>
```
CI (`Jenkinsfile`) installs `tests/requirements-pbt.txt` and passes `--hypothesis-seed="$BUILD_NUMBER"`, archiving the seed and log (PBT-08).

### 3. Property-based testing (PBT Partial)
- Framework: Hypothesis (PBT-09). Shrinking is enabled; property tests set `print_blob=True`, so failures print a reproduction blob; runs are seeded (PBT-08).
- Generators live in `tests/rustfs/strategies.py`: product-group sets, access levels, buckets, generated and shuffled policy documents (PBT-07).
- Properties: P1 JSON round-trip (PBT-02); P2 order-insensitive canonical form, P3 allow-only bucket scope, P4 group-union equals the per-bucket maximum, P5 accepted iff canonically equal (PBT-03).

### 4. Review results
A failing property prints the shrunk example and blob; replay it with `@reproduce_failure` or the same `--hypothesis-seed`.
