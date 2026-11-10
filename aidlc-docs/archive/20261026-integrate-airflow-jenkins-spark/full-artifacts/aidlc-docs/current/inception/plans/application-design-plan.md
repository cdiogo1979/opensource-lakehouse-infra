# Application Design Plan — Airflow, Jenkins, and Spark Integration

## Context and Scope

The approved execution plan calls for Application Design because Airflow and Jenkins are joining the target Compose platform and the Airflow-created Spark driver, existing Spark worker, Git Bundles, Kerberos, Hive Metastore, and RustFS need explicit service contracts. This stage defines component responsibilities and high-level interfaces; detailed behavior belongs in per-unit Functional Design.

The current canonical architecture says Airflow/Jenkins are deferred. The approved requirements take precedence and establish these design constraints:

- Airflow and Jenkins are services in the target Compose project and join `iceberg-poc-net`.
- Airflow uses the project Git repository for pinned, read-only Git Bundle revisions and creates one ephemeral Spark driver per run.
- The driver submits to the existing Spark master/workers.
- The driver and worker use the existing Kerberos writer principal and RustFS writer credentials through protected runtime files.
- Jenkins validates code only and does not need to publish or update bundle refs.
- Preserve existing lakehouse services, persistent data, JupyterHub behavior, StarRocks behavior, and identity boundaries.

## Execution Checklist

- [x] Review approved requirements, stories, reverse-engineering findings, and canonical application/workload designs.
- [x] Resolve the design questions below and check for contradictions. Answers A/A/A are consistent with the approved requirements; see the recorded decisions.
- [x] Define component ownership and high-level responsibility boundaries.
- [x] Define high-level method/interface signatures and inputs/outputs; leave detailed rules to Functional Design.
- [x] Define Airflow, Spark, Jenkins, and existing lakehouse service interactions.
- [x] Document the component dependency matrix and data flow.
- [x] Generate `aidlc-docs/current/inception/application-design/components.md`.
- [x] Generate `aidlc-docs/current/inception/application-design/component-methods.md`.
- [x] Generate `aidlc-docs/current/inception/application-design/services.md`.
- [x] Generate `aidlc-docs/current/inception/application-design/component-dependency.md`.
- [x] Generate `aidlc-docs/current/inception/application-design/application-design.md` as the consolidated active design.
- [x] Validate consistency against requirements, stories, and existing component boundaries. The Spark master-advertised hostname is intentionally left for Infrastructure Design to verify against the current worker URL (`spark://spark-iceberg:7077`) and Compose DNS.
- [x] Request explicit review and approval of the design artifacts.

## Design Questions

Please fill each `[Answer]:` tag. These choices affect service ownership and runtime boundaries. If none of the options match, choose X and describe the needed approach.

### Question 1 — Airflow metadata database ownership

How should Airflow's metadata database be deployed within the target project?

A) Keep the sibling setup's dedicated Airflow PostgreSQL service and named volume, isolated from Hive metastore PostgreSQL.

B) Use a separate Airflow database on the existing target PostgreSQL server, with an independently managed database and credentials.

X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 2 — Spark worker ticket-cache ownership

Where should the writer TGT cache lifecycle run for the existing Spark service, which currently starts the master, worker, and history server in one container?

A) Keep credential acquisition and renewal within the existing Spark service startup/runtime boundary, using a private runtime cache alongside Spark.

B) Add a separate credential helper service that owns renewal and shares a private cache volume with the Spark service.

X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 3 — Jenkins Docker socket boundary

The approved NFR requirement says to constrain Docker socket access for Airflow and Jenkins, and the sibling Compose file mounts the socket in Jenkins. The inspected Jenkins pipeline itself only runs Python compilation and tests and does not invoke Docker. Which boundary should the design use?

A) Preserve the existing Jenkins Docker socket mount to match the approved requirement and sibling Compose setup, while keeping Jenkins CI-only.

B) Remove Docker socket access from Jenkins because its current validation pipeline does not use it. This changes the approved NFR scope and requires updating and re-approving the requirements and affected stories.

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Recorded Answers So Far

- **Question 1 — A**: Keep Airflow's dedicated PostgreSQL service and named volume, separate from Hive metastore PostgreSQL.
- **Question 2 — A**: Keep TGT acquisition and renewal inside the existing Spark service boundary, with a private runtime cache.
- **Question 3 — A**: Preserve Jenkins's existing Docker socket mount to match the approved NFR and sibling Compose setup. The inspected Jenkinsfile does not currently invoke Docker; retaining the mount preserves the selected topology and carries a significant host-control risk.

## Design Decisions Already Fixed by Requirements

- Do not replace the run-pinned Git Bundle contract with mutable live source mounts.
- Do not change the existing writer principal or rotate credentials.
- Do not move the Airflow driver to local-only Spark execution.
- Jenkins does not publish artifacts or modify Airflow bundle references.
- Keep UAT/production endpoints unconfigured and distinct from local dev.
- Keep the Airflow metadata database separate from the Hive metastore database; Question 1 selects whether it has a separate service or shares only the PostgreSQL server process.

## Approval Gate

After questions are answered and any ambiguity is resolved, generate the design artifacts and request explicit approval before proceeding to Units Generation.

**Status**: Design artifacts are complete and awaiting explicit approval.
