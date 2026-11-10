# Unit Test Instructions — Airflow Keycloak SSO

## Run the repository unit suite

Install the test tools and existing Hub runtime dependencies in a temporary environment. Use the Hub module path because the Hub container configures it at runtime:

```bash
python3 -m venv .venv-ci
.venv-ci/bin/python -m pip install -r tests/requirements-pbt.txt
.venv-ci/bin/python -m pip install -r infra/jupyter/hub/requirements.txt
PYTHONPATH=infra/jupyter/hub .venv-ci/bin/python -m pytest -q tests --hypothesis-seed=20261030
```

The current Jenkinsfile command omits the Hub runtime dependencies and module path; the local command above supplies these existing project dependencies without changing CI configuration. Live provider-mutating tests are opt-in and remain skipped unless their explicit environment flags are set. Do not set those flags for this verification.

## Focused regression tests

```bash
PYTHONPATH=infra/jupyter/hub .venv-ci/bin/python tests/keycloak/test_airflow_client_contract.py
PYTHONPATH=infra/jupyter/hub .venv-ci/bin/python tests/airflow/test_keycloak_sso_contract.py
PYTHONPATH=infra/jupyter/hub .venv-ci/bin/python tests/keycloak/test_jupyterhub_client_contract.py
```

These cover the exact Airflow callback, client flags, mapper reconciliation, group-role matrix, deny-by-default behavior, local-admin collision protection, local password route restrictions, and unchanged JupyterHub client contract.

## Expected results

- All repository tests pass; opt-in live tests are skipped under the approved non-mutating test boundary.
- The focused SSO contract suites and existing JupyterHub contract suite pass.
- No test writes to a persistent Keycloak realm or performs an interactive login.
