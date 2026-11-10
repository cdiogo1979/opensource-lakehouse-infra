# Integration Test Instructions — Unit 4

## Scope

Unit 4 verifies the integrated Hub, Keycloak, Spark, Polaris, and RustFS path. Source contracts run without provider access. Live role-matrix checks are opt-in because they create temporary Keycloak service clients, temporary Polaris principals, and unique smoke-table rows before cleanup.

## Source contract checks

From the repository root, run the ordinary test command used by CI. The `integration` and `live` markers are registered in `pytest.ini`; the provider-mutating test is skipped unless explicitly enabled.

```bash
python3 -m pytest -q tests/integration
```

## Opt-in live role matrix

Prerequisites: Docker is available; the local Keycloak, Polaris, RustFS, and Spark image are ready; protected bootstrap credentials exist; and the operator has reviewed the exact live test boundary. The existing verifier creates only run-prefixed service clients and Polaris principals and writes only unique rows in the three approved smoke tables.

```bash
LAKEHOUSE_LIVE_ROLE_MATRIX=1 python3 -m pytest -q tests/integration/test_unit4_spark_polaris_contract.py
```

This invokes `scripts/verify-role-matrix.py`. The verifier attempts cleanup in its `finally` path and reports a cleanup marker. If the command is interrupted or cleanup is not confirmed, stop and inspect only the unique `rm-<run-id>` clients/principals and probe rows before rerunning. Do not manually delete any pre-existing identity, grant, table, or object.

The role matrix covers developer, analyst, owner, and writer behavior across production/UAT/dev and validates table locations. It uses temporary service-account identities; it is not browser OIDC acceptance and does not prove direct RustFS out-of-scope access denial or exact STS session policy/lifetime.

## Manual browser acceptance

Follow `e2e-test-instructions.md` for developer and analyst browser sign-in, unapproved-group denial, isolated server/home checks, user-token expiry behavior, and cleanup. Keep temporary human credentials out of test environment variables and artifacts.

## Remaining checks

- Direct RustFS access denial outside the exact vended session scope and actual STS policy/duration are unverified.
- The exact client behavior at vended-credential refresh after the 300-second Keycloak token expires is unverified; expected fail-closed behavior must be distinguished from successful refresh.
- A strict five-second end-to-end STS deadline is not established by current per-stage timeout settings.
- Two-user live concurrency, performance measurements, and deferred resiliency scenarios need separate recorded evidence. Resiliency owner: platform operator. Schedule date: unset.

## Cleanup

The role-matrix command must report both `ROLE_MATRIX_CLEANUP` and `Temporary identity cleanup completed.`. Confirm the smoke tables contain only their original rows and the temporary credential file is absent. Stop the stack with `scripts/lakehouse.sh stop` when approved. This preserves named volumes and bucket contents; never use `docker compose down -v` for routine cleanup.
