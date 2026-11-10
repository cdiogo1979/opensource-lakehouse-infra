# Application Design — Platform Spark Session Helper

Consolidates [components.md](components.md), [component-methods.md](component-methods.md), [services.md](services.md) and [component-dependency.md](component-dependency.md). Backed by probes in throwaway containers on 2026-11-10; no running service changed.

## Decisions
1. **The module ships with the workload environment**: `infra/workload-python/python/{lakehouse_spark,lakehouse_broker_client}.py`, copied to `/opt/lakehouse/python/` in both images. Moving them out of `infra/jupyter/singleuser/` puts them next to the lock they are delivered with.
2. **Import path through the venv**: `lakehouse-platform.pth` (one line, `/opt/lakehouse/python`) in the venv's `site-packages`. It works whatever `PYTHONPATH` is, so Airflow run containers (`PYTHONPATH=/opt/lakehouse-bundle`) can import it; the venv check is unaffected (a path entry is not an installed distribution). Jupyter's `PYTHONPATH` drops `/opt/lakehouse`.
3. **One source of catalog settings**: `lakehouse_spark.catalog_settings()`. `spark-defaults.conf` keeps only the Iceberg extensions and the redaction patterns; its `lakehouse` catalog lines go. The smoke bootstrap is unaffected (it sets every catalog key, with `oauth2`).
4. **Token source**: `airflow` when `LAKEHOUSE_TOKEN_PROVIDER=airflow` (all run settings required); otherwise `jupyter` when `JUPYTERHUB_API_TOKEN` is set (the module requests the user's token and sets the provider variables); otherwise an error. No fallback between them.
5. **Existing session**: returned when its default catalog matches; otherwise an error asking for a kernel restart. Replaces today's unconditional refusal in `lakehouse_spark` and the silent `getOrCreate` reuse in `job_runtime`.
6. **Compatibility of the order**: the current repository code keeps working with the new images: it sets its own catalogs (allowed), and its Jupyter path imports `lakehouse_broker_client`, which the `.pth` still provides.
7. **Notebook values from library code**: `IPython.get_ipython().user_ns` is the notebook's namespace, also while a `%run` script executes (`sys.modules["__main__"]` is not, during `%run`). The widget helper reads `WIDGET_LIST` and keeps widgets in `LAKEHOUSE_WIDGETS` there; `parse_task_args` and `task_args` read it, and `TASK_ARGS`, the same way.
8. **Run versus import**: both `%run` scripts act only when `__name__ == "__main__"` and `ipykernel` is loaded; imported as `notebooks.common...` (as Airflow runs and tests do), they define functions only.
9. **Application name**: from `JPY_SESSION_NAME` (Jupyter Server 2.21.1 sets it to the notebook's path for kernels it starts): `<env>-<notebook file stem>`; `<env>-notebook` when unset.
10. **Widgets**: `ipywidgets==8.1.9` in `requirements.in` (the lock adds it with `jupyterlab_widgets` 3.0.17 and `widgetsnbextension` 4.0.16); `jupyterlab_widgets==3.0.17` in JupyterLab's requirements, the same version as the kernel's. The Airflow runtime image gets the packages too (one lock), unused there.

## Probe results
| Probe | Result |
|---|---|
| `.pth` in the runtime venv, `spark-submit` with `PYTHONPATH=/opt/lakehouse-bundle` | the module imports; `/opt/lakehouse/python` on `sys.path`; `check-venv` still OK (53 packages) |
| `ipywidgets` against the lock (runtime base) | 8.1.9 resolves with `jupyterlab_widgets` 3.0.17 and `widgetsnbextension` 4.0.16; no locked version changes |
| `jupyterlab_widgets` 3.0.17 against JupyterLab's pins | resolves alone |
| Kernel prototype (Jupyter image, `ipywidgets` 8.1.9) | `%run` script read `WIDGET_LIST` from `user_ns`; widget views emitted; a second `%run` kept the typed value; library code read `{'entity': 'orders', 'scale_factor': ''}` and `TASK_ARGS`; `__main__` is not `user_ns` during `%run` |
| `JPY_SESSION_NAME` | set by Jupyter Server 2.21.1 (`sessionmanager.py`) to the notebook path |
| Smoke bootstrap | sets extensions, redaction and every catalog key itself (`oauth2`) |

## Canonical knowledge
As planned: UPDATE `application-design.md`, `workload-python-environment.md` (the module, the `.pth`, `ipywidgets`), `airflow-workflows.md` (the repository-side contract).
