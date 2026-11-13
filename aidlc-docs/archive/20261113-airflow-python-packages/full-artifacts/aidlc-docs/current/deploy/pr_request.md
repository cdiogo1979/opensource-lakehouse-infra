# PR request — Airflow on the slim image with fixed Python packages; broker upgrades

## Problem
The Airflow image was built on the full `apache/airflow` image: 30 providers and 2 727 packages, most unused (Google with `ray` and its jars, Snowflake, Azure, `litellm`), with 266 fixable findings, 5 critical (Authlib, uv, certifi). The token broker ran FastAPI 0.115 with Starlette 0.46, cryptography 45 and the base's pip 23.

## Solution
- Airflow on `apache/airflow:slim-3.3.2-python3.10` (pinned by digest) with only the providers the platform uses (fab, standard, git, docker, postgres) plus authlib, pymysql, and httpx2 and graphviz (without them, warnings on stdout break the CLI's JSON output), all selected by the 3.3.2 constraints.
- `infra/airflow/security-overrides.txt`: pinned fixed releases newer than the constraints (Authlib, GitPython, urllib3, PyJWT, Mako, Werkzeug, certifi, joserfc, msgpack, uv, setuptools, pip), installed after them; the build runs `pip check`. The `prek` dev tool is removed; the system Python's pip and setuptools are upgraded.
- The admin bootstrap and broker viewer scripts ignore Python warnings, so a library warning can't break their JSON user listing.
- Broker: FastAPI 0.162.5, Starlette 1.7.0, cryptography 50.0.2, pip 26.3, `pip check`.
- Tests for the base, providers, overrides and pins; docs.

## Verification
667 tests passed, 3 skipped; broker unit tests and DAG factory tests pass in the new images; scan: no fixable critical in either image (Airflow 266 -> 6 fixable findings, broker 33 -> 2); live: Airflow restarted, bundles registered, SSO redirect and login, UAT DAG runs succeeded, role matrix passed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
