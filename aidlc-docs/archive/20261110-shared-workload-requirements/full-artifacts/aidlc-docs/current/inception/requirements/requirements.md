# Requirements — Shared Workload Requirements

## Intent Analysis
- **Request**: one common requirements file for all workload code, used by both the Airflow Spark containers and the Jupyter Spark environment. Products can add their own extras, constrained by the platform pins, and Jupyter runs Python 3.10 like the Spark runtime (CR-2 of `20261110-platform-dag-factory`).
- **Type**: platform enhancement (images, Airflow runs, Jupyter, CI), brownfield.
- **Scope**:
  - **This workspace**: the requirements and lock, both images, the DAG factory, the validator, Jupyter configuration, verifiers, README, tests.
  - **The workload repository**: docs only.
- **Complexity**: moderate.
- **Depth**: standard.
- **Answers**: Q1 to Q8 in `requirement-verification-questions.md`.

## Functional Requirements

### FR-1 Platform base requirements and lock (Q2 A)
- **Location**: `infra/workload-python/requirements.in` lists the top-level packages: PyYAML, requests, pandas, numpy, pyarrow, ipykernel, jupytext. The first version keeps the versions the Airflow runtime has today where they exist (PyYAML 6.0.2, requests 2.32.3, pandas 2.2.3, numpy 1.26.4, pyarrow 17.0.0).
- **The lock**: `infra/workload-python/requirements.lock` pins every package, dependencies included, as `name==version`, for Python 3.10 on the platform's architecture.
- **Regenerating it**: a platform script resolves the lock inside the Spark runtime image (same Python and architecture). The lock is never edited by hand.
- **PySpark**: comes from the shared Spark 3.5.5 distribution (`/opt/spark/python` and its py4j), not from pip. Both images carry the identical `/opt/spark`. scipy, matplotlib and pyiceberg are no longer available to workload code unless added later.

### FR-2 One environment at one path in both images (Q1 A)
- **The venv**: both `local/lakehouse-spark-runtime` and `local/lakehouse-jupyter-singleuser` contain `/opt/lakehouse/venv`, a Python 3.10 venv holding exactly the lock, and `/opt/lakehouse/requirements.lock`.
- **The Spark runtime**: builds the venv from its Python 3.10. `PYSPARK_PYTHON` and `PYSPARK_DRIVER_PYTHON` point at the venv, so `spark-submit` drivers and executors use it. The base image's other packages are not visible to workload code.
- **Jupyter**: builds the venv from its own Python 3.10 (Ubuntu, so not copied from the runtime image), at the same patch version where available. Local Spark in the kernel uses the venv.

### FR-3 Jupyter kernel (Q5 A)
- **One kernel**: "Lakehouse (Python 3.10)", backed by `/opt/lakehouse/venv`, is the only kernel and the default. The conda Python 3.13 kernel is no longer offered to users.
- **JupyterLab**: keeps running on its own Python.
- **Unchanged**: the kernel's environment keeps today's Spark settings (`SPARK_HOME`, `PYTHONPATH` with `/opt/spark/python` and `/opt/lakehouse`, the token provider). Notebooks with the old kernel name open with the new kernel.

### FR-4 Product extras in Airflow (Q3 A)
- **Declaring them**: a product repository may have an optional `requirements.txt` at its root. The bundles check it out, so `sparse_dirs` gains the root file.
- **Installing them**: every DAG gets a task `install_requirements` between `create_cluster` and `validate_environment`. It runs `pip install -r /opt/lakehouse-bundle/requirements.txt --constraint /opt/lakehouse/requirements.lock` in the run's container, into a run-local location on the venv's path. It does nothing when the file is absent.
- **Failures**: a conflict with the lock or an install failure fails the task, so no workload code runs and cleanup still happens. The output is redacted.
- **Pins hold**: extras can add packages but can never change a locked version.

### FR-5 Product extras in Jupyter (Q4 A)
- **The command**: `lakehouse-install-requirements [PATH]`, available in the Jupyter image and documented, installs a repository's `requirements.txt` with the platform lock as constraint. It goes into a per-user location the kernel sees, persisted in the user's home, and works from a terminal or with `!` in a cell.
- **Nothing automatic**: a kernel restart picks up new packages.

### FR-6 Checks (Q6 A, B, C)
- **Image build check**: both Dockerfiles fail unless the venv's installed packages (`name==version`, excluding pip and setuptools) equal the lock, and Python is 3.10.
- **CI extras check**: `lakehouse-validate-workflows` also checks a product `requirements.txt`, when present, by resolving it against the platform lock (a dry run). A conflict, or a line that isn't a plain requirement (for example `-e`, `--index-url` or a URL), fails CI. The lock is available read-only in Jenkins.
- **Live parity verifier**: `scripts/verify/workload-python-parity.sh` checks that both built images report the same Python minor version and exactly the same packages and versions in `/opt/lakehouse/venv`, both equal to the lock.

### FR-7 Workload repository (Q7 A)
- **Docs**: `README.md` and `AGENTS.md` describe the platform base set, how to add `requirements.txt` extras (constrained, installed each run), the Jupyter command, and the single kernel.
- **Example extras for `default`** (CR-1): `requirements.txt` with `duckdb==1.5.6`.
- **TPC-H test workload** (CR-2): `notebooks/workload/generate_tpch.py` and `workflows/generate_tpch.json`, described under CR-2.
- **Delivery**: pushed to `main` and `uat` only after the user's approval.

### FR-8 Documentation and tests
- **Platform README**: covers the shared environment, regenerating the lock, the extras in Airflow and Jupyter, and the checks.
- **Knowledge docs**: updated at closure.
- **Tests**:
  - lock format and parse;
  - the extras line rules;
  - the image check logic;
  - the Dockerfile and Compose contracts;
  - the DAG factory's `install_requirements` task;
  - Hypothesis properties.
- **Live**:
  - both images build and the parity verifier passes;
  - a UAT run passes;
  - a run with a temporary extras file installs it, using a throwaway bundle copy or a branch only with approval;
  - a Jupyter kernel starts on 3.10 with pandas available.

## Change request CR-1 (2026-11-10, during Requirements Analysis)
- **Request**: "as example i want to add the dependency to pytpch 0.2.0".
- **Finding**: `pytpch` 0.2.0 (and 0.1.0) is published only as `cp310-manylinux_2_34_x86_64`, with no source distribution. The platform is ARM (`aarch64`), and the Spark runtime has glibc 2.31. `pip download --only-binary=:all: pytpch==0.2.0` in the runtime image finds no matching distribution, so it can't be installed in either image.
- **Decision** (user: "A different TPC-H package"): `default` gets an example `requirements.txt` with `duckdb==1.5.6`, which replaces Q7 A for this point.
  - **Install**: the wheel is `manylinux_2_26/2_28_aarch64`, and it has no dependencies.
  - **TPC-H generation**: verified in the runtime image (`CALL dbgen(sf=0.01)` gives 60,175 `lineitem` rows).
  - **Network**: its `tpch` extension is downloaded from `extensions.duckdb.org` at first use, so a run that generates TPC-H data needs that network access in its fresh container.
  - **No pytpch**: `pytpch` is not added. The README explains why such a package can't be used (wheel platform and glibc), and the CI extras check reports it.
- **Live test**: the example exercises the extras path end to end (CI check, `install_requirements`, an import in the run container, and the Jupyter command).

## Change request CR-2 (2026-11-10, during Workflow Planning)
- **Request**: "can you add a test_tcph workload which generates and count the rows in the dataset generated and that takes as a parameter the tcph entity name?" Named `generate_tpch` (TPC-H), renamed from `test_tpch` at the user's request, with tasks `generate_<entity>`.
- **Answers** (interactive): one task per entity; check expected counts.
- **Entry point**: `notebooks/workload/generate_tpch.py` in the workload repository.
  - **Arguments**: the standard `--environment` and `--config-dir`, then after `--` (read with `notebooks.common.cli.task_args()`): `--entity <name>` (required) and `--scale-factor <sf>` (optional, default 0.01).
  - **Entity**: one of `region`, `nation`, `supplier`, `customer`, `part`, `partsupp`, `orders`, `lineitem`; anything else is a usage error.
  - **Scale factor**: a number greater than 0 and at most 1, so the test stays small.
  - **Behavior**: imports `duckdb` (the CR-1 extras), runs `CALL dbgen(sf=<sf>)` in an in-memory database, counts the entity's rows, and prints the entity, scale factor and count.
  - **Check**: fails (non-zero exit) unless the count matches TPC-H: `region` 5 and `nation` 25 at any scale; `supplier` 10,000, `customer` 150,000, `part` 200,000, `partsupp` 800,000 and `orders` 1,500,000, each times the scale factor; `lineitem` between 1 and 7 times the `orders` count (each order has 1 to 7 lines).
  - **Verified** in the runtime image with `duckdb==1.5.6`: at 0.01, 5, 25, 100, 1,500, 2,000, 8,000, 15,000 and 60,175 rows; at 0.1, 5, 25, 1,000, 15,000, 20,000, 80,000, 150,000 and 600,572.
  - **Jupyter**: runs from a notebook after `lakehouse-install-requirements`, with the arguments given directly (`task_args()` is empty there).
- **Workflow**: `workflows/generate_tpch.json`, `schedule` null, tag `tpch`, eight independent tasks `generate_<entity>`, each with `entrypoint` `generate_tpch.py` and `args` `["--entity", "<entity>"]`. They all run after `validate_environment`, inside the same run container.
- **Consequences**:
  - **Extras**: the workflow depends on the `requirements.txt` extras, so it is the end-to-end test of FR-4. The factory's `install_requirements` runs once per DAG run, before the eight tasks.
  - **Network**: each task downloads DuckDB's `tpch` extension on first use in the run container (CR-1). The first task caches it in the container's home for the others, provided that home is writable; Application Design confirms this.
  - **Spark**: `spark-submit` runs the script as a Python application. It doesn't start a Spark session.
- **Tests**: unit tests in the workload repository for argument parsing and the expected-count rule (with Hypothesis over the scale factor). The workflow passes the platform validator.

## Change request CR-3 (2026-11-10, during Build and Test)
- **Finding**: `start-airflow` recreates the token broker's Airflow Viewer user (`ensure-broker-viewer.py`). The broker caches its Viewer API token until shortly before it expires, and dropped it only on 401. Airflow answers a token of the recreated user with **403**, so every DAG run failed at `create_cluster` ("Airflow bundle check failed (HTTPStatusError)") until the broker restarted. Seen live twice on 2026-11-10; the "transient failure" of the previous intent's UAT run was probably the same.
- **Decision** (user: "Fix it in this intent"): on 401 or 403 from the DAG lookup, the broker drops the cached token, signs in again and retries once. A second refusal is `503 service_unavailable` as before; no writer token is issued.
- **Tests**: the fake Airflow refuses tokens issued before the Viewer was recreated; one test for the single re-sign-in, one for a refusal that persists.
- **Live**: a run after a second `start-airflow`, with no broker restart, succeeds.

## Change request CR-4 (2026-11-10, during Build and Test)
- **Finding**: in the interactive test, `git` was not available in the Jupyter user server, so a product repository couldn't be cloned there (README step "Clone this repository into your workspace").
- **Request**: "we need to install the git jupyter plugin".
- **Decision**: the Jupyter single-user image installs Ubuntu's `git` (2.53.0) and the JupyterLab Git extension `jupyterlab-git==0.55.0` (with `nbdime` 4.0.4) into JupyterLab's own Python; JupyterLab stays at 4.3.5. Repositories are public and cloned anonymously over HTTPS; no Git credentials are configured.
- **Verified**: `git --version` as `jovyan`; `jupyterlab_git` and `nbdime` server extensions enabled; `@jupyterlab/git` 0.55.0 lab extension enabled; GitHub reachable from user servers; parity verifier still OK.

## Change request CR-5 (2026-11-10, during Build and Test)
- **Finding**: the user servers' persistent volume is mounted at `/home/jovyan/work`, not `/home/jovyan`, and the Hub removes stopped containers. So `~/.local/lakehouse/python3.10` (FR-5, Application Design decision 7) does not survive a server restart, contrary to "persisted in the user's home". The README also said the whole home directory was a volume.
- **Decision** (user: "Keep it per session"): no code change. The folder lasts for the server session; the platform and workload READMEs say to rerun `lakehouse-install-requirements` after every server start, and the platform README states that only `~/work` persists. FR-5's "persisted in the user's home" is superseded.
- **Context** (asked by the user): user servers run as the Jupyter Docker Stacks' fixed user `jovyan` (UID 1000); isolation is one container and one volume per Hub user, and data access uses the user's own Keycloak identity.

## Change request CR-6 (2026-11-10, during Build and Test)
- **Finding** (analysis of the workload helpers): the Git bundles had no `subdir`, so Airflow treated the whole checkout as the DAG folder. Its safe-mode heuristic matched `notebooks/workload/count_sample_rows.py` (its own comment mentions "Airflow" and "DAGs"), and the DAG processor imported it from both bundles about every 30 seconds, executing repository code at parse time.
- **Decision** (user: "yes fix it"): `BUNDLE_KWARGS` and `validate-bundle-config.py` add `"subdir": "dags"`. The stub still takes the repository root from its own path, so workflows, the Spark container mount, the bundle identity and the DAG IDs are unchanged. Applying it recreates Airflow once (`start-airflow`).
- **Verified**: after `start-airflow`, the DAG processor parsed only `lakehouse.py` in each bundle and nothing under `notebooks/`; all four DAGs verified; `default-uat-generate_tpch` 13/13.

## Non-Functional Requirements
- **NFR-1 Determinism**: the same lock gives the same packages in both images. Nothing workload code imports is left unpinned by the platform.
- **NFR-2 Isolation**:
  - Extras never change locked versions.
  - Run-time installs happen only inside the run's own container.
  - Jupyter installs go only into the user's own location.
- **NFR-3 No secrets**: no index credentials. PyPI is public and reached anonymously.
- **NFR-4 Run cost**: no extras means no network access and no time cost. With extras, the install time is part of the run and documented.
- **NFR-5 Image size**: the venv adds only the locked packages (no pip PySpark).

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q8: A) |
| Property-Based Testing | Partial (PBT-02, 03, 07, 08, 09 enforced) | Requirements Analysis (Q8: A) |
| Resiliency Baseline | No | Requirements Analysis (Q8: A) |
| Workflow Conventions | Yes (always enforced) | Workflow start |

## Out of scope
- Private package indexes.
- Caching extras across runs (Q3 B).
- Automatic installation in Jupyter (Q4 B).
- Upgrading Spark or Python beyond 3.10.
- JupyterLab's own environment.
- The enforcing bundle class.
