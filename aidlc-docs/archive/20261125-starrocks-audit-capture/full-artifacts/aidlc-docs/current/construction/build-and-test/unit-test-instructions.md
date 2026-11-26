# Unit Test Execution — StarRocks Audit Capture

| Command | Result 2026-11-26 |
|---|---|
| `python -m pytest -q -p no:cacheprovider` (host venv) | 729 passed, 3 skipped |
| `scripts/verify/dag-factory-tests.sh` (Airflow image) | 119 passed |
| `scripts/verify/broker-unit-tests.sh` | 13 passed |
| `scripts/verify/docs-links.py` | no broken links |

Hypothesis properties (PBT-02, -03, -07, -08): plugin.conf and package round trips, column check, install decision, product-block levels, table-grant render and parse round trip, token expiry, settings validation. Seeds are Hypothesis defaults with the repository's fixed settings; failures print their reproduction blob.
