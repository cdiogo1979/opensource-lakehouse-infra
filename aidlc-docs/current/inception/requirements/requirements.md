# Requirements — Python packages in the Airflow and token broker images (20261113-airflow-python-packages)

Approved by the user ("yes proceed" to the next cleanup step, with recommended decisions as before).

## Intent
After the OS upgrades, the Airflow image still had 197 fixable language findings (5 critical: Authlib, uv x2, certifi x2), most from software the platform doesn't use: the full `apache/airflow` image carries 30 providers (Google with `ray` and its jars, Snowflake, Azure, `litellm`, ...). The broker had cryptography 45 and Starlette 0.46 (via FastAPI 0.115) and the base's pip 23.

## Functional requirements
- **FR-1** Airflow is built on `apache/airflow:slim-3.3.2-python3.10` (pinned by digest) with only what the platform uses: providers `fab` (auth manager), `standard` (operators), `git` (DAG bundles), `docker` (the Docker SDK for Spark containers), `postgres` (metadata database), plus `authlib` (OAuth login) and `pymysql` (MV deploy), selected by Airflow's 3.3.2 constraints.
- **FR-2** A pinned `security-overrides.txt` upgrades, after the constrained install, the packages whose fixes are newer than the constraints (Authlib, GitPython, urllib3, PyJWT, Mako, Werkzeug, certifi, joserfc, msgpack, uv, setuptools); the build runs `pip check` and fails on any conflict.
- **FR-3** The `prek` developer tool (with its own `uv`) is removed; the system Python's pip and setuptools are upgraded.
- **FR-4** The broker pins FastAPI 0.162.5, Starlette 1.7.0 and cryptography 50.0.2, and upgrades pip and setuptools.
- **FR-5** The platform still works: Airflow SSO login roles, DAG bundles, a UAT DAG run (broker, Spark container, MV deploy); broker unit tests pass in the new image.
- **FR-6** Docs updated.

## Decisions (recommended, accepted)
- Not upgraded, with reasons: dnspython 2.9 needs Python 3.11 (Airflow runs 3.10); opentelemetry-api 1.45 needs the matching SDK and exporters (one medium finding); pip's vendored certifi, msgpack, urllib3 and pkg_resources wait for a pip release; `rustls` inside the `uv` binary (low/medium) waits for a uv release.
- Overrides are reviewed when Airflow moves to a new release (its constraints then supersede them).
