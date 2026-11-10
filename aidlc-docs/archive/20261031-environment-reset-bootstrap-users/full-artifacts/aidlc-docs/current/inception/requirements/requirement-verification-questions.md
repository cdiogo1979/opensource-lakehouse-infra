# Requirements Verification Questions — Environment Reset and Bootstrap Users

Context: `aidlc-docs/current/inception/reverse-engineering/`.

## Question 1 — What `role-platform-admin` grants
`role-platform-admin` is a new group. No service grants it anything today. What should it grant?

A) The same rights as `role-default-owner` in every service: Polaris product roles, RustFS all S3 actions on the three buckets, Airflow Admin, Jenkins Administer, and JupyterHub admission (Recommended)

B) Make `platform-admin` a member of both `role-platform-admin` and `role-default-owner`; no new service mappings, so `role-platform-admin` is a label

C) A label only: `role-platform-admin` grants nothing yet

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2 — Default password behavior
How should the shared default password `ChangeM3!` behave?

A) Temporary: each user must change it at first login (Recommended)

B) Permanent: users keep `ChangeM3!` until changed manually

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 3 — Reset scope
What should the full reset delete?

A) All v2 state:
- core and Airflow volumes
- Jupyter user home volumes and runtime containers
- v2 networks
- `.runtime/credentials/`, `.runtime/container-mounts/`, and `.runtime/airflow-dag-bundles/`

Keep the `local/lakehouse-*` images, other projects' volumes, files in the sibling `opensource-lakehouse` repository, and `.runtime/aidlc-test-venv` (Recommended)

B) As A, and also remove the `local/lakehouse-*` images

C) As A, and also delete the Airflow Bundle checkouts in `../opensource-lakehouse/.runtime/airflow-dag-bundles`

X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 4 — Reset safety
How should the reset be confirmed?

A) `scripts/lakehouse.sh reset --confirm`: refuses without the flag, prints the exact inventory first, and offers a `--dry-run` that changes nothing (Recommended)

B) An interactive prompt: the operator types `reset` to proceed

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 5 — Where bootstrap users are created
Where should the bootstrap users be created?

A) In `infra/keycloak/bootstrap-realm.py`, which runs during `lakehouse.sh start`. Users are created only if missing, and existing users' passwords are never reset (Recommended)

B) Only in `scripts/bootstrap-default-product.sh`

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6 — Existing users
`joe-developer` and `platform-admin` already exist in the current realm. How should existing users be handled?

A) Ensure the group membership, but leave existing passwords untouched. After a reset, every user is created fresh with the default password (Recommended)

B) Also reset existing users' passwords to `ChangeM3!`

X) Other (please describe after [Answer]: tag below)

[Answer]: X — "this should run after the reset "environment" , so they should not exist. nevertless if you run twice the user bootsrap you should reset the passwords and groups assignment to the default"

## Question 7 — Writer identities
How should `srv-default-writer` relate to the existing `write-service-account` client, which Airflow and Spark use?

A) Keep `write-service-account` unchanged. `srv-default-writer` is an additional password user in `role-default-writer` (Recommended)

B) Replace the service-account membership with `srv-default-writer`

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 8 — Startup flow
What should the documented startup be?

A) Keep two steps: `scripts/lakehouse.sh start`, then `scripts/bootstrap-default-product.sh`. Airflow stays an optional `start-airflow` (Recommended)

B) Make `scripts/lakehouse.sh start` run the full product bootstrap too

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 9 — Testing the adjusted startup
What does "tested" mean for this intent?

A) A full local cycle:
- reset, then start, then product bootstrap
- check that every bootstrap user exists in the right group and can log in, with Polaris principals reconciled
- rerun the existing verification scripts (RustFS, Jenkins, Polaris writer, Spark smoke)
- confirm the reset leaves nothing behind

Plus automated contract tests (Recommended)

B) Automated contract tests plus reset and start only

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 10 — Existing narrow reset script
What should happen to `infra/polaris/reset-default-product-once.py`, which only empties buckets and catalogs?

A) Keep it, and document the new full reset as the primary reset (Recommended)

B) Retire it in favor of the full reset

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 11 — Security Baseline extension
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)

B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 12 — Property-Based Testing extension
Should property-based testing (PBT) rules be enforced for this project?

A) Yes — enforce all PBT rules as blocking constraints

B) Partial — enforce PBT rules only for pure functions and serialization round-trips

C) No — skip all PBT rules

X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 13 — Resiliency Baseline extension
Should the resiliency baseline (directional AWS Well-Architected Reliability practices; not a production certification) be applied?

A) Yes

B) No

X) Other (please describe after [Answer]: tag below)

[Answer]: B
