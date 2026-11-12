# Build and Test Summary — Jupyter Vulnerabilities

| Check | Result |
|---|---|
| Rebuilt images | `local/lakehouse-jupyter-singleuser:6.1.1-spark` (JupyterLab 4.6.5, notebook 7.6.4), `local/lakehouse-jupyterhub:6.1.1`; `apt`/`libapt-pkg7.0` 3.2.1ubuntu0.1 in both |
| Trivy, HIGH/CRITICAL, Jupyter-owned (Spark jars and pyarrow excluded) | single-user ~40 packages -> 7; Hub 9 -> 1 |
| Remaining, with reasons | `/opt/lakehouse/venv` pip 23.0.1 (vendored certifi, msgpack, urllib3) and setuptools 65.5.0: workload environment, same in the Spark runtime, deferred to the workload-lock intent; nbclassic 1.3.3 (latest) underscore 1.13.7 and MathJax 2.7.9: no fix released, classic UI not served; setuptools 70.3.0 entry in the Hub's system Python: not the Hub's environment (`/srv/venv` has 84.2.1) |
| Host pytest | 653 passed, 3 skipped (new: no Lab/notebook pin, constrained install) |
| `scripts/verify/workload-python-parity.sh` | OK: 56 packages in both images; one kernel, Lakehouse (Python 3.10) |
| Live (user) | "worked fined": sign-in, server, kernel; the running Hub and user server use the rebuilt images (JupyterLab 4.6.5, notebook 7.6.4 confirmed in the server) |
