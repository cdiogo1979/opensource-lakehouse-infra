# Requirements — Jupyter Vulnerabilities

Depth: standard (two images on the users' path, the Hub in the sign-in path).

## Request
"in the meantime start an intent to close jupyter reported vulnabilities"

## Answers
- Base: **6.1.1-7** (same JupyterHub 6.1.1, rebuilt 2026-11-07; multi-arch digests): `jupyterhub/jupyterhub@sha256:48973496688583afca1c29571c7e69849ed9b9ffb74874af29b2c87e787aa8c6`, `jupyterhub/singleuser@sha256:4f4b2240f6645834fe68358ac4b0c2e1fc4d0c70549910d682281fee352c3fd6`.
- Lab pins: **use the base's versions** (drop `jupyterlab` and `notebook` pins; keep `ipykernel`, `jupytext`, `jupyterlab-git`, `jupyterlab_widgets` in step with `ipywidgets` in the workload lock).
- Scope: **Spark jars and pyarrow out** (Spark base intent; workload-lock intent).

## Baseline (Trivy, HIGH and CRITICAL, built images)
- Single-user, Jupyter's own: JupyterLab 4.3.5 (5 CVEs) and notebook 7.3.2 (2) from our pins; in `/opt/conda`: Brotli 1.2.0 (CRITICAL), certifi 2026.7.22 (CRITICAL), msgpack 1.1.2, oauthlib 4.0.0, urllib3 2.7.0, setuptools 70.3.0, zip 8.6.0 in `rattler.abi3.so` (CRITICAL); nbclassic's underscore 1.13.7 and MathJax 2.7.9 (no fix); Ubuntu `apt`, `libapt-pkg7.0`; Go `stdlib` in `/usr/bin/pebble`.
- JupyterHub: follow-redirects 1.16.0 (Node, the proxy), msgpack, oauthlib, urllib3, setuptools, `apt`, `libapt-pkg7.0`, `libbrotli1`, pebble's Go `stdlib`.

## Functional requirements
- **FR-1** Both Dockerfiles pin the 6.1.1-7 digests.
- **FR-2** `infra/jupyter/singleuser/requirements.txt` no longer pins `jupyterlab` or `notebook`; a test refuses pins that downgrade them.
- **FR-3** After the rebuild, each remaining Jupyter-owned HIGH/CRITICAL finding with a fix is patched in the Dockerfile (Python packages upgraded in the server and Hub environments within the Hub's lock; OS packages with `apt-get install --only-upgrade`; Node packages where the proxy allows); findings without a fix are listed in the build-and-test summary with their reachability.
- **FR-4** The platform still works: JupyterHub sign-in with Keycloak, a server spawn, the Lakehouse kernel with Spark reading a table as the user, the Git sidebar, Jupytext notebooks, widgets.
- **FR-5** Docs: JupyterHub reference (versions); known limitations (whether the arm64-only Jupyter pin remains: the single-user image still copies the arm64 JDK from the Spark runtime).

## Non-functional
- **NFR-1** Tests: image contract tests updated; the parity check between the image and the workload lock still passes.
- **NFR-2** Re-scan: Jupyter-owned HIGH/CRITICAL findings drop to those without a released fix; the workflow's next run closes the matching alerts.
