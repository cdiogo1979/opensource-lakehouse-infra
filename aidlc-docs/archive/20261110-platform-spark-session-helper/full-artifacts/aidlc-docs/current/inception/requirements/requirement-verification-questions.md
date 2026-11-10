# Requirement Verification Questions — Platform Spark Session Helper

Asked and answered interactively on 2026-11-10. Background: `../reverse-engineering/spark-session-helper.md`.

## Q1 Who owns what
A) Platform session, repository config: one platform module starts the session (token source, catalogs, redaction); the repository keeps `config_loader` and `cli`; `start_spark_job` becomes a thin wrapper (Recommended)

B) Platform session and config

C) Only clean up the repository

X) Other

[Answer]: X, then A after a follow-up. The user's point: "the data product repo config files will have much more info than just the data product config also present in the platform. also prod and uat jobs that run in airflow should get the config information . example , i may have a config regarding a source dataset , and it maybe different for dev , uat and prod". Follow-up confirmed: the repository keeps free-form `configs/<env>.yml` (all keys passed to jobs in Jupyter and Airflow, as now); only the session setup moves to the platform, using the config's `catalog_name`.

## Q2 Product configs in Jupyter
A) An optional notebook override (Recommended)

B) The Hub sets it from the user's groups

C) Not needed

X) Other

[Answer]: The user asked "in jupyter , why do you need the LAKEHOUSE_PRODUCT?". Explained: only for repositories serving several products with `configs/<product>/`; Airflow knows the product from the bundle, a Jupyter clone doesn't. Follow-up answer: C, not needed; Jupyter uses `configs/<env>.yml`, and the README says product folders apply in Airflow only.

## Q3 Environment in Jupyter
A) Default `dev`; a notebook may choose `uat` or `prod` before the helper (Recommended)

B) `dev` only

[Answer]: A

## Q4 Task arguments in Jupyter
A) `TASK_ARGS` in the notebook; `task_args()` returns it in Jupyter (Recommended)

B) Keep per-notebook variables

[Answer]: A

## Q5 Extensions
A) Property-based testing, partial; Security and Resiliency off (Recommended)

B) All off

[Answer]: A

## Q6 Workload repository delivery
A) Prepared and tested in the scratchpad clone; pushed to `main` and `uat` after approval; platform side first and compatible with the current repository code (Recommended)

B) A pull request only

[Answer]: A
