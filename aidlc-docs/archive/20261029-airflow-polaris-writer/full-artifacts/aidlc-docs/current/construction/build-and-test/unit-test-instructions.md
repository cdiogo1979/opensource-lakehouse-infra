# Unit Test Execution

## Infrastructure repository

Run the configured suite, including broker, configuration, contract, and enforced property-based tests:

```bash
PYTHONPATH=infra/jupyter/hub python3 -m pytest -q
```

## Workload repository

Run the full Jenkins unit-test command:

```bash
python3 -m pytest -q
```

Run its read-only compilation and quality checks:

```bash
python3 -m compileall -q airflow_bundle_client.py dags notebooks
scripts/code_quality.sh all
```

Record the actual test count, pass/fail result, and any environmental limitations in the Build and Test summary. No test result implies UAT runtime, concurrency, or resilience verification.
