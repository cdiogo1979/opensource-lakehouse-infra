# Requirement Verification Questions — Cleanup and Modular Compose

Answer each question by putting the letter after the `[Answer]:` tag.

## Question 1 — Root Jenkinsfile
The root `Jenkinsfile` runs this repository's tests, but Jenkins has no job for this repository. What should happen to it?

A) Remove it; Jenkins CI is for the workload repository only (Recommended)

B) Keep it for a future CI job for this repository

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2 — Jenkins migration code
The legacy Jenkins is gone, so `scripts/migrate-jenkins-home.py` now only writes a "fresh" marker, and `lakehouse.sh remove-legacy-jenkins` has nothing left to remove. What should happen to them?

A) Remove both. Jenkins simply starts with its home volume, and the related README text and tests go too (Recommended)

B) Keep them as they are

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3 — Broken Spark smoke tests
`run-bootstrap-smoke-spark.sh` and the Spark part of `verify-role-matrix.py` use a legacy image that no longer exists. Today the product bootstrap stops at that step. After a reset, the StarRocks smoke read also has no tables to read. What should happen?

A) Repoint both to the current Spark runtime image (`local/lakehouse-spark-runtime:3.5.5_1.10.2`) and fix what that needs, so the bootstrap runs end to end again (Recommended; slightly larger than pure cleanup)

B) Remove the Spark smoke step and the role-matrix Spark part, and have the StarRocks bootstrap skip its smoke read when the tables are absent

C) Leave them as a follow-up

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4 — Compose file naming
How should the Compose files be named?

A) `compose.core.yml`, `compose.jupyter.yml`, `compose.jenkins.yml`, `compose.airflow.yml`, `compose.starrocks.yml`. The two existing files are renamed, giving one consistent pattern (Recommended)

B) Keep the `docker-compose.` prefix: `docker-compose.core.yml`, `docker-compose.jupyter.yml`, `docker-compose.jenkins.yml`, plus the existing Airflow and StarRocks files

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5 — Turning modules on and off
How should the modules be selected?

A) Core always runs. Jupyter, Jenkins, and StarRocks run with `start` by default, each with an opt-out in `.env` (`JUPYTER_ENABLED`, `JENKINS_ENABLED`, `STARROCKS_ENABLED`). Airflow keeps its own `start-airflow` command (Recommended)

B) A single `.env` list, `LAKEHOUSE_MODULES=core,jupyter,jenkins,starrocks,airflow`, with `start` running exactly those modules. Airflow joins the normal start when listed

C) All modules always run; the files are split for organization only

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6: Security Extensions
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)

B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 7: Property-Based Testing Extension
Should property-based testing (PBT) rules be enforced for this project?

A) Yes — enforce all PBT rules as blocking constraints (recommended for projects with business logic, data transformations, serialization, or stateful components)

B) Partial — enforce PBT rules only for pure functions and serialization round-trips (suitable for projects with limited algorithmic complexity)

C) No — skip all PBT rules (suitable for simple CRUD applications, UI-only projects, or thin integration layers with no significant business logic)

X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 8: Resiliency Extensions
Should the resiliency baseline be applied to this project?

A) Yes — apply the resiliency baseline as directional best practices and design-time guidance (recommended for business-critical workloads, as an informed starting point that you can validate and harden before go-live)

B) No — skip the resiliency baseline (suitable for PoCs, prototypes, and experimental projects where rapid iteration matters more than reliability)

X) Other (please describe after [Answer]: tag below)

[Answer]: B
