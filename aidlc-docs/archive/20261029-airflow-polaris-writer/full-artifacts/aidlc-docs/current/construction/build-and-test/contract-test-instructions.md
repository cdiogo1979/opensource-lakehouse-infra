# Contract Test Instructions

Run the repository unit suites that validate the broker OpenAPI contract, Airflow registration and renewal behavior, Spark provider configuration, Bundle names/refs, and Compose service boundaries:

```bash
python3 -m pytest -q
```

Also validate the merged Compose configuration and build the Spark runtime and broker images. Record individual observed results in the Build and Test summary. Runtime calls to the writer broker are limited to the approved main production workflow after readiness checks.
