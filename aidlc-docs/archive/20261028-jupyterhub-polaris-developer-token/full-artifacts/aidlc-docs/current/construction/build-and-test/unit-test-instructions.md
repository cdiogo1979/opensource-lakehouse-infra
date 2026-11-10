# Unit and Source Contract Test Execution

## Full suite

The host may not include pytest, Hypothesis, or Tornado. Build the Hub image first, then run the full suite in a disposable container. The repository is mounted read-only, and pytest/Hypothesis caches are disabled:

```bash
docker run --rm --mount type=bind,src="$PWD",dst=/workspace,readonly \
  -w /workspace local/lakehouse-jupyterhub:6.1.1 \
  sh -lc 'python -m pip install --disable-pip-version-check --no-cache-dir -r tests/requirements-pbt.txt && PYTHONPATH=/etc/jupyterhub PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider -q tests'
```

`tests/requirements-pbt.txt` pins pytest, Hypothesis, and Tornado. The live role-matrix integration test remains skipped unless `LAKEHOUSE_LIVE_ROLE_MATRIX=1` is explicitly set; it creates temporary provider identities and unique smoke-table rows and must be run only with the approved local test scope and cleanup readiness.

## Host-only checks

The following source suites can run on a host with the project runtime dependencies installed:

```bash
python3 -m unittest discover -s tests/jupyterhub -p 'test_*.py' -v
python3 -m unittest discover -s tests/keycloak -p 'test_*.py' -v
```

The Hub tests import Tornado. A missing host dependency is an environment limitation; use the full container suite above rather than interpreting that collection error as a product test failure. Repository-root default unittest discovery does not recurse into these test directories.

## Results

The current suite contains Unit 1–4 source and contract tests. Coverage is not measured because no target is defined. Pytest writes results to stdout; no report file is produced.
