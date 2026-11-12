# JupyterHub

Reference: notebooks with Spark, signed in as yourself. Back to the [README](../../README.md).

- **Who gets in**: the groups each product file lists under `apps.jupyterhub` (by default developers and analysts), and `role-platform-admin`. The files are read at every sign-in. Platform admins are also Hub admins: they can see, stop, and open other users' servers. Admission is checked at login and again before each server starts.
- **Your server**: each user gets one Spark server (default 1 CPU and 2 GiB; at most two servers run at once). Your `~/work` folder is a named volume that survives server restarts; the rest of the home directory (`/home/jovyan`, the image's fixed Jupyter user) is reset when the server restarts. Settings: `JUPYTERHUB_SINGLEUSER_CPU_LIMIT`, `JUPYTERHUB_SINGLEUSER_MEMORY_LIMIT`, `JUPYTERHUB_HOST_PORT`. Each notebook with a Spark session holds 1 to 1.5 GiB until its kernel shuts down, so run one Spark notebook at a time.
- **Spark in a notebook** — data access is your own:

  ```python
  from lakehouse_spark import create_spark_session
  spark = create_spark_session()
  ```

  The Hub's internal token broker renews your Keycloak token over TLS. Polaris issues the storage credentials. Product repositories wrap this in their own start-up (`start_spark_job`); see the [workload Python environment](workload-python.md).
- **Checkpoint keys**: your server gets the `dev` checkpoint keys of the products where you are owner or developer ([Streaming checkpoints](streaming-checkpoints.md)).
- **Versions**: JupyterHub 6.1.1 (`jupyterhub/jupyterhub` and `jupyterhub/singleuser` 6.1.1-7, pinned by multi-architecture digest). JupyterLab and notebook are the base image's own (4.6.5 and 7.6.4); `infra/jupyter/singleuser/requirements.txt` adds `ipykernel`, `jupytext`, `jupyterlab-git` and `jupyterlab_widgets`, and the build is constrained to the base's JupyterLab and notebook, so an extension can never downgrade them.
- **Widgets**: `ipywidgets` works in the kernel (JupyterLab has the matching `jupyterlab_widgets`), for example for a notebook's input fields.
- **Git**: user servers have `git` and the JupyterLab Git extension (the Git sidebar), so you can clone a product repository into `~/work`, for example `git clone https://github.com/cdiogo1979/opensource-lakehouse-sample-dp.git`. No Git credentials are stored on the platform.
- **Kernel**: the only kernel is **Lakehouse (Python 3.10)**, the same Python and packages as Airflow's Spark runs (see [Workload Python environment](workload-python.md)). Notebooks saved with the earlier `python3` kernel open with it. JupyterLab itself runs on its own Python.
- **A product's extra packages**: in a terminal, or with `!` in a cell, run `lakehouse-install-requirements` in the product repository (or `lakehouse-install-requirements path/to/repo`), then restart the kernel. They go to `~/.local/lakehouse/python3.10` and never change the platform's versions. That folder is outside `~/work`, so it lasts only for the current server session: **rerun the command after every server start**. After a platform lock change the command asks you to rerun it with `--reset`.
- **Network**: user servers run on the `jupyter-user` network (default `172.30.240.0/24`, Hub at `172.30.240.2`). If start reports a subnet conflict, change `JUPYTER_USER_SUBNET` and `JUPYTERHUB_BROKER_BIND_IP` together.
- **Rotating broker trust**:
  1. `./scripts/lakehouse.sh stop`
  2. `python3 scripts/setup/prepare-jupyterhub-broker-certificates.py --rotate`
  3. `./scripts/lakehouse.sh start`
