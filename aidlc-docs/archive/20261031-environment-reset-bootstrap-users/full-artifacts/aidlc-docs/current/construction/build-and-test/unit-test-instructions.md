# Unit and Contract Test Execution

```sh
python3 -m pytest -q -p no:cacheprovider tests --ignore=tests/jupyterhub/test_unit2_token_broker.py
PYTHONPATH=infra/jupyter/hub python3 -m pytest -q -p no:cacheprovider tests/jupyterhub/test_unit2_token_broker.py
```

Expected: 184 passed, 1 skipped, 2 failed, plus 10 passed for the broker tests. The 2 failures are the earlier Airflow developer-role drift in `tests/airflow/test_keycloak_sso_contract.py`. They are out of scope.

The new test files are:

| File | What it covers |
|---|---|
| `tests/keycloak/test_bootstrap_users_contract.py` | the user and group set, permanent password, platform-admin to owner, writer client, create-only realm bootstrap, enforcement plan, writer consumers |
| `tests/operations/test_reset_lakehouse.py` | inventory selection, the full volume and network lists, path guard, confirmation word, a non-interactive run needs `--yes`, mutually exclusive flags |
| `tests/airflow/test_bundle_root_contract.py` | no sibling-repository reference, the Bundle root inside this repository, host validation with `--host-paths`, container validation without a host path |
