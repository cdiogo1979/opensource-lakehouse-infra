# Unit and Contract Tests

```sh
python3 -m pytest -q -p no:cacheprovider tests --ignore=tests/jupyterhub/test_unit2_token_broker.py
PYTHONPATH=infra/jupyter/hub python3 -m pytest -q -p no:cacheprovider tests/jupyterhub/test_unit2_token_broker.py
```

Expected: 217 passed, 1 skipped, plus 2 earlier Airflow drift failures (out of scope). The broker tests pass (10).

`tests/operations/test_compose_modules_contract.py` (10 tests) checks:
- the module files and the services in each
- the project name, set only in core
- unchanged resource names
- retired files absent and unreferenced
- every Compose invocation names its files
- the flag-built file list
- five rendered module combinations
- the Spark runtime image and auth
- reproducible builds
- orphan handling
