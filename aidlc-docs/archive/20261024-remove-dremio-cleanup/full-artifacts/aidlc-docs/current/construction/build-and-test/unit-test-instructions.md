# Unit Test Instructions

## Automated unit tests

No unit-test suite is present in this infrastructure repository. The cleanup did not change pure business logic or serialization helpers, so no new unit tests or property-based tests were added.

## Available local checks

The following checks were executed successfully:

- `docker compose config --quiet` — Compose syntax and interpolation.
- `bash -n` over the startup, provisioning, cleanup, TPCH, Spark, Kerberos, and Hive shell scripts — shell syntax.
- Python `ast.parse` over seven repository Python files — Python syntax without importing runtime dependencies or creating bytecode.
- Targeted Compose assertions — Dremio and `tpch-jdbc` services absent; relocated Spark, TPCH loader, and generator paths present.

These checks are syntax/configuration checks, not behavioral unit tests. There are no test reports or coverage figures.
