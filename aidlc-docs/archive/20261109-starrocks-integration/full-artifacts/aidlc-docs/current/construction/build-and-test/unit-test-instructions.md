# Unit, Contract, and Property Tests

```sh
python3 -m pytest -q -p no:cacheprovider tests --ignore=tests/jupyterhub/test_unit2_token_broker.py
PYTHONPATH=infra/jupyter/hub python3 -m pytest -q -p no:cacheprovider tests/jupyterhub/test_unit2_token_broker.py
```

Expected: 219 passed and 1 skipped, plus 2 earlier Airflow drift failures in `tests/airflow/test_keycloak_sso_contract.py`, which are out of scope. The broker tests pass (10).

StarRocks tests (`tests/starrocks/`, 33 tests):
- `test_starrocks_properties.py`: Hypothesis P1–P8, with `print_blob=True`
- `test_starrocks_compose_contract.py`: images, ports, networks, volumes, no secret values, only the TLS runtime mounts, the entrypoint, and the certificate and login TLS
- `test_starrocks_bootstrap_contract.py`: opt-out, the empty or failed Keycloak abort, the missing-roles abort, non-JWT and root users untouched, JWT SQL, catalog conflict and recreate, unrecognized grants, wiring, legacy retirement, the backend column, and the Polaris read privilege
