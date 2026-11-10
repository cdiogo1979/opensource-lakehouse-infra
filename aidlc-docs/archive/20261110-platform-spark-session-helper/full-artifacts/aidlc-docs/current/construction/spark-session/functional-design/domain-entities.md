# Domain Entities — spark-session

| Entity | Form | Rules |
|---|---|---|
| **Catalog** | `lakehouse`, `lakehouse_uat`, `lakehouse_dev` | The platform's Polaris catalogs; one is the session's default |
| **Token source** | `airflow` or `jupyter` | Chosen from the process environment (BR-S3) |
| **Environment** | `dev`, `uat`, `prod` | Airflow: from `--environment`; Jupyter: `LAKEHOUSE_ENVIRONMENT`, default `dev` |
| **Config** | `EnvironmentConfig` from `config_loader` | Repository-owned, free-form; `catalog_name` selects the default catalog |
| **Argument declaration** | mapping of name → spec | Name `[a-z][a-z0-9_]{0,49}`; spec `{"required": True}` or `{"default": "<text>"}` or `{}` |
| **Option** | `--` + name with `_` → `-` | `scale_factor` → `--scale-factor` |
| **Task arguments** | list of strings | Airflow: after `--`; Jupyter: `TASK_ARGS` |
| **Widget registry** | `LAKEHOUSE_WIDGETS` in the notebook: name → `ipywidgets.Text` | Built from `WIDGET_LIST` |
| **Parsed arguments** | read-only mapping name → string or `None` | Every declared name present |
| **Context** | Jupyter when `ipykernel` is loaded; otherwise a script (`spark-submit`, tests) | Decides sources and error behavior |
