# Requirement Verification Questions — Shared Workload Requirements

Asked and answered interactively on 2026-11-10. Background: `../reverse-engineering/shared-workload-requirements.md`.

## Q1 How the pinned workload environment is built
A) A clean venv at the same path (`/opt/lakehouse/venv`, Python 3.10, exactly the lock) in both images, used by Spark and the Jupyter kernel (Recommended)

B) Install the lock over the runtime's existing Python

X) Other

[Answer]: A

## Q2 Contents of the first platform base file
A) The current Airflow data stack (PySpark 3.5.5 Python side, PyYAML, requests, pandas, numpy, pyarrow, plus ipykernel and jupytext), pinned with their dependencies (Recommended)

B) Everything the runtime has (146 packages)

C) Minimal

X) Other

[Answer]: A

## Q3 Product extras in Airflow
A) An optional `requirements.txt` at the repository root, installed in each run's container with `--constraint <platform lock>` before `validate_environment`; a conflict or failure fails the run before any code runs (Recommended)

B) The same, cached per bundle commit

C) No product extras

X) Other

[Answer]: A

## Q4 Product extras in Jupyter
A) A documented command installs them into the user's kernel environment; nothing automatic (Recommended)

B) Automatic at kernel start

X) Other

[Answer]: A

## Q5 The existing Jupyter kernel (conda Python 3.13)
A) Replaced: "Lakehouse (Python 3.10)" is the only kernel; JupyterLab keeps its own Python (Recommended)

B) The new kernel is the default; the old one is kept

X) Other

[Answer]: A

## Q6 Checks (multiple choice)
A) An image check at build: the venv holds exactly the lock (Recommended)

B) A CI extras check: the validator resolves the product `requirements.txt` against the lock (Recommended)

C) A live parity verifier for both images (Recommended)

X) Other

[Answer]: A, B and C

## Q7 Workload repository
A) Docs update (README, AGENTS.md); no `requirements.txt` for `default`; pushed to `main` and `uat` after approval (Recommended)

B) Also an example `requirements.txt`

C) No workload change

X) Other

[Answer]: A, changed by CR-1: an example `requirements.txt` with `duckdb==1.5.6` (the `pytpch` 0.2.0 the user asked for can't be installed: it has an x86_64 glibc 2.34 wheel only)

## Q8 Extensions
A) Property-based testing, partial; Security and Resiliency off (Recommended)

B) All off

X) Other

[Answer]: A
