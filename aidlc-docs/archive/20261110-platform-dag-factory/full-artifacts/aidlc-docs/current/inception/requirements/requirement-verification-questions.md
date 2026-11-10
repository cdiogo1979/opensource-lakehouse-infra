# Requirement Verification Questions — Platform DAG Factory

Asked and answered interactively on 2026-11-10. Background: `../reverse-engineering/platform-dag-factory.md`.

## Q1 How the platform package reaches Airflow
A) Baked into the Airflow image (Recommended)

B) Read-only mount into the dag-processor and the scheduler

X) Other

[Answer]: B — read-only mount

## Q2 Where the environment-config check runs
A) In the run's Spark container, with the repository's own `config_loader` (Recommended)

B) In the scheduler, as today

X) Other

[Answer]: A

## Q3 Supported DAG declaration
A) JSON only; the stub loads `workflows/*.json`; CI flags extra `.py` files under `dags/` (Recommended)

B) JSON and the Python API

X) Other

[Answer]: A

## Q4 Workflow JSON fields (v1)
A) Today's fields plus description and tags (Recommended)

B) Also retries and timeouts

C) Also task arguments (plus retries and timeouts)

X) Other

[Answer]: C

## Q5 How task arguments reach the job
A) Extra argv after `--`; the repository's `cli.py` returns the extras (Recommended)

B) A `LAKEHOUSE_TASK_ARGS` environment variable

X) Other

[Answer]: A

## Q6 Accepted bundle names
A) Product bundles only (`<product>-main`, `<product>-uat`); legacy `lakehouse-*` and the `dev` fallback dropped (Recommended)

B) Keep legacy and dev

X) Other

[Answer]: A

## Q7 CI validation of `workflows/*.json`
A) A validator in the Jenkins image, run by the repository's `Jenkinsfile` (Recommended)

B) Airflow import errors only

X) Other

[Answer]: A

## Q8 Delivery of the workload repository change
A) Prepared and tested in the scratchpad clone; pushed to `main` and `uat` after approval, once the platform side is live (Recommended)

B) A patch for the user to apply

X) Other

[Answer]: A

## Q9 Extensions
A) Property-based testing, partial; Security and Resiliency off (Recommended)

B) PBT partial plus Security

C) All off

X) Other

[Answer]: A

## Q10 Enforcing bundle class
A) Later phase (Recommended)

B) Include it now

X) Other

[Answer]: A
