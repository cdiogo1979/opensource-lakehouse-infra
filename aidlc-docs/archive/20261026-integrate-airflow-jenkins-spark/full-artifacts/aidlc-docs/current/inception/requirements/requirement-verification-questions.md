# Requirements Clarification Questions

Please answer each question by filling the `[Answer]:` tag. These choices define which parts of the Airflow/Jenkins/Spark setup are integrated and how Spark receives its lakehouse identity.

## Question 1 — Airflow and Jenkins deployment scope
How should the sibling orchestration stack be brought into this project?

A) Add/adapt the Airflow and Jenkins Compose services, images, and required mounts in this lakehouse project, sharing its `iceberg-poc-net` network.

B) Keep Airflow and Jenkins deployed separately; update only the Spark image/configuration and documented connection to this lakehouse.

C) Add Airflow to this project, but keep Jenkins separate and use it only as an external CI gate.

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 2 — Git DAG Bundle source of truth
The local Airflow 3 bundle checkout is generated runtime state for a separate Git repository. Which repository should Airflow fetch for the integrated DAGs and workloads?

A) Move/maintain the required DAG factory, DAGs, configs, and workload code in this lakehouse project, and configure bundles to fetch this project's Git repository.

B) Keep the separate `opensource-lakehouse` bundle repository as the source of truth; integrate only the Airflow/Spark runtime here.

C) Keep the existing repository and bundle configuration unchanged; only alter runtime Spark credentials/configuration.

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 3 — Spark container execution model
The current bundle factory creates one container per DAG run, mounts that run's bundle read-only, and runs Spark in `local[*]`. What should the integrated workflow do?

A) Preserve this per-run container and local Spark execution model; mount the exact run-pinned bundle read-only.

B) Preserve ephemeral per-run containers, but configure their jobs to submit to the existing target Spark master/worker service.

C) Replace per-run containers with one long-running shared Spark service for Airflow jobs.

X) Other (please describe after [Answer]: tag below)

[Answer]:B

## Question 4 — Spark writer identity
Which identity should Spark workloads use to access Hive Metastore and RustFS?

A) Use the existing Kerberos principal `write-service-account@LAKEHOUSE.LOCAL` and its matching RustFS writer credentials. This is the target project's ETL identity; it is separate from StarRocks SQL user `write_service_account`.

B) Create a new Airflow-specific Kerberos principal and RustFS identity, leaving the existing writer identity for the TPCH loader only.

C) Use only the StarRocks SQL account `write_service_account` for Spark. Note: this SQL account cannot authenticate Spark to Hive Metastore or RustFS.

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 5 — Credential delivery to ephemeral containers
The current DAG factory does not mount or initialize the lakehouse writer keytab or RustFS credentials. What integration boundary should provide them?

A) Extend Airflow's per-run container creation and Compose configuration to mount the keytab read-only, use a private ticket cache, obtain/verify the TGT, and provide RustFS credentials as file-backed secrets; keep bundle code read-only.

B) Keep the DAG factory unchanged and require the Airflow host/deployment to inject an already-authenticated ticket cache and RustFS credentials into each Spark container.

C) Configure credentials only in Spark defaults/environment variables, without mounting a keytab or secret files.

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 6 — Jenkins responsibility
The inspected Git bundle repository's Jenkinsfile validates code but does not publish artifacts or change Airflow bundle refs. What should Jenkins do in the integrated project?

A) Bring in the Jenkins service and retain its CI validation role only; Git bundles continue to fetch from the configured Git repository.

B) Bring in Jenkins and have it also publish/update the development bundle ref using the existing protected branch-selection workflow.

C) Do not include Jenkins in this integration; retain it as an independently operated CI service.

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 7 — Environment targets
The bundle code supports `dev`, `uat`, and `prod`, while this target Compose lakehouse is a single local environment. Which behavior is intended?

A) Integrate all three bundle identities/config files, but point only `dev` at the local lakehouse; leave UAT/prod targets as explicit placeholders for future environments.

B) Integrate only a local `dev` bundle/config now; add UAT/prod when their lakehouse environments exist.

C) Route all three bundle identities to this same local lakehouse for now.

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 8 — Security Baseline extension
Should the Security Baseline extension rules be enforced as blocking constraints for this integration?

A) Yes — enforce the Security Baseline rules (recommended when Docker socket access and credentials are involved).

B) No — skip Security Baseline rules for this local PoC.

X) Other (please describe after [Answer]: tag below)

[Answer]:B

## Question 9 — Property-Based Testing extension
Should Property-Based Testing rules be enabled?

A) Yes — apply all PBT rules.

B) Partial — apply PBT only to applicable pure functions and serialization round-trips.

C) No — do not enable PBT for this thin integration.

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 10 — Resiliency Baseline extension
Should the Resiliency Baseline be applied as directional design guidance?

A) Yes — apply the baseline as design guidance; it does not certify availability or production readiness.

B) No — skip the baseline for this local PoC.

X) Other (please describe after [Answer]: tag below)

[Answer]:B
