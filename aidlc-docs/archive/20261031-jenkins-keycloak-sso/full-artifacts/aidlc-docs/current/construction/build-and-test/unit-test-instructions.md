# Unit Test Execution — jenkins-keycloak-sso

```bash
python3 -m pytest -q tests/jenkins tests/keycloak tests/rustfs
PYTHONPATH=infra/jupyter/hub python3 -m pytest -q tests --hypothesis-seed=<seed>   # full suite, as in CI
```
- `tests/jenkins/`: plugin pins and Dockerfile; configuration as code (endpoints, claims, secrets, escape hatch, exact matrix); Compose, secrets, start ordering, and guarded removal; migration decision table and copy safety.
- `tests/keycloak/test_jenkins_client_contract.py`: client, mapper, port resolution, port-move reconciliation, refusals, and contract JSON.
- The PBT extension is disabled; no property tests are required.
