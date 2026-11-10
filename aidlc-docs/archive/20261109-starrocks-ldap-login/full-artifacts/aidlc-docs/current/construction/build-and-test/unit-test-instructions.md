# Unit (Contract and Property) Test Instructions

```sh
PYTHONPATH=infra/jupyter/hub python3 -m pytest -q tests
```

- **Property-based tests** (Hypothesis, partial mode, PBT-02/03/07/08/09):
  - `tests/ldap/test_ldap_people_properties.py`: P1 LDIF round trip; P2 verification before deletion; P3 coverage; P5 password precedence; P6 idempotency (advisory)
  - `tests/starrocks/test_starrocks_properties.py`: P2 JWT users switched, never recreated; P6 the LDAP user plan converges; P8 desired state gives an empty plan
  - **Shared generators**: `tests/ldap/ldap_strategies.py`.
- **Reproducing a failure**: Hypothesis prints the falsifying example and a `@reproduce_failure` blob (`print_blob=True`). Replay with `python3 -m pytest tests/ldap --hypothesis-seed=<seed>`, or paste the blob as a decorator. Shrinking is never disabled.
- **Result**: 354 passed, 1 skipped, 1 failed. The failure is the known Airflow developer-role drift.
