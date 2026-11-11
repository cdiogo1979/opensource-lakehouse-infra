# Requirement Verification Questions — Spark S3 Checkpoints

Asked and answered interactively on 2026-11-11.

## Q1 Credentials for checkpoints
A) RustFS STS `AssumeRoleWithWebIdentity` with the job's own token (writer in Airflow, user in Jupyter), limited by policy to the checkpoint prefix (Recommended) — B) Static per-product checkpoint keys — C) Polaris-vended table credentials

[Answer]: A

## Q2 Location
A) `s3://<bucket>/checkpoints/` in each product environment bucket (Recommended) — B) Under the namespace location

[Answer]: A

## Q3 Access
A) Like table writes: the writer in Airflow runs; developers in dev only from Jupyter; owners like developers; analysts read only; never another product's prefix (Recommended) — B) Writers only

[Answer]: A

## Q4 Extensions
A) Security Baseline enforced and property-based testing partial; Resiliency off (Recommended) — B) PBT partial only

[Answer]: A
