# Unit of Work Definitions — Airflow, Jenkins, and Spark Integration

## Purpose

This brownfield decomposition assigns the approved stories to four component-aligned implementation units. Units are review and sequencing boundaries, not new deployable services. One maintainer owns the full integration. Complete the units sequentially and review the published interface contracts before moving to the next unit.

## Shared Constraints

- Keep the local Docker Compose target, `iceberg-poc-net`, and existing lakehouse services and named volumes.
- Reuse the existing `write-service-account` Kerberos and RustFS credentials without rotation.
- Keep Git Bundle revisions pinned and mounted read-only; each Airflow DAG run creates one ephemeral Spark driver and one ephemeral Spark worker, then removes both. Worker registration uses the shared Spark master and does not guarantee exclusive executor placement.
- Keep Airflow's metadata PostgreSQL service/volume separate from Hive metastore PostgreSQL.
- Preserve selected Docker socket mounts and document their host-control boundary; Jenkins remains CI-only.
- Keep UAT/production as unconfigured placeholders, never silently mapped to dev.
- Verify the Spark master-advertised endpoint against Compose DNS and the current worker startup URL (`spark://spark-iceberg:7077`) during Infrastructure Design.
- Preserve user data and existing runtime credential files; no volume reset is permitted as a normal integration or rollback step.

## Units

### Unit 1 — Spark Writer Runtime

**Outcome**: Existing and Airflow-created Spark workers can use the writer identity for Hive Metastore and RustFS access, and worker-only startup/readiness behavior is documented alongside the remote driver contract.

**Ownership boundary**: Existing Spark runtime (`infra/spark/`, Spark configuration, and its existing Compose service settings where necessary).

**In scope**:

- Initialize and renew the writer Kerberos TGT within the existing Spark service boundary using a private runtime cache.
- Retain read-only keytab and file-backed RustFS credential handling.
- Define Spark submission, master advertisement, executor callback, and worker identity expectations for Unit 2.
- Provide the worker-only runtime mode and writer credential/readiness contract used by Unit 2's per-run worker containers; retain the long-lived worker for notebooks and other clients.
- Keep the existing Spark master/worker/history-server role and data unchanged beyond the approved writer runtime configuration.

**Stories**: US-03.

**Exit contract**: Documented and reviewable credential/cache lifecycle and Spark endpoint contract. The actual advertised endpoint and executor connectivity are verified during Infrastructure Design and Build and Test.

**Out of scope**: Airflow DAG or bundle management; new identities; per-author delegated lakehouse authorization; changes to Hive/RustFS data layout.

### Unit 2 — Airflow Bundle Runner

**Outcome**: Airflow resolves a pinned bundle for each run, starts one ephemeral Spark driver and one ephemeral Spark worker, submits remotely to the shared Spark cluster, reports the result, and removes both containers on success or failure. Worker lifecycle is dedicated per run, but executor placement is shared across registered workers.

**Ownership boundary**: Existing Airflow Git Bundle checkout, DAG factory, DAG declarations, and run-container integration reviewed from the sibling project. Confirm target paths against the maintained source before implementation.

**In scope**:

- Preserve the selected Git Bundle revision as an immutable, read-only run input.
- Configure local `dev` access and fail clearly or remain unavailable for unconfigured UAT/production.
- Supply the driver's read-only writer keytab and RustFS secret files and use a private per-run ticket cache.
- Create one worker-only Spark container per run using Unit 1's worker credential/runtime contract; await its TGT readiness and Spark-master registration, then remove it with the driver. Admit at most two runs concurrently; queue additional runs.
- Submit using the Unit 1 Spark contract; propagate task status and ensure driver cleanup after both success and failure.
- Keep credential values out of bundle/source content, ordinary environment variables, and logs.

**Stories**: US-01, US-02, US-04, US-06.

**Dependencies**: Unit 1's reviewed Spark endpoint, execution, and writer credential contract.

**Exit contract**: Reviewed bundle-to-driver contract, run lifecycle, environment selection behavior, secret-file mount contract, and cleanup behavior.

**Out of scope**: Creating or rotating the writer identity; exclusive placement of a DAG run's executors on its per-run worker; publishing or moving Bundle references from Jenkins.

### Unit 3 — Platform Compose Integration

**Outcome**: Airflow and Jenkins run as part of the target Compose project and can reach required lakehouse and Docker resources while existing services and data remain intact.

**Ownership boundary**: Target `docker-compose.yml` and new/relocated Airflow/Jenkins image, configuration, and runtime infrastructure files.

**In scope**:

- Integrate Airflow 3 API server, scheduler, DAG processor, triggerer, initialization, and a dedicated PostgreSQL service and volume.
- Integrate Jenkins with its persistent home and the approved Docker socket mount.
- Join relevant services and per-run drivers/workers to `iceberg-poc-net`; define host-visible bundle/credential paths and image build contexts.
- Apply the Unit 1 and Unit 2 service contracts and preserve existing services, ports, network, volumes, identities, and data.
- Document the Airflow scheduler and Jenkins Docker socket mounts and the additional host-control risk of Jenkins's unused-by-current-pipeline mount.

**Stories**: cross-cutting support for US-02, US-04, and US-05; requirement FR-1 and NFR-5.

**Dependencies**: Reviewed interface contracts from Units 1 and 2.

**Exit contract**: Compose-level ownership, mounts, network, dependencies, and persistent-volume behavior are reviewable without starting or resetting the target stack.

**Out of scope**: Altering lakehouse catalog/data or independently deploying UAT/production environments.

### Unit 4 — Jenkins Validation

**Outcome**: Jenkins validates repository changes without deploying services, publishing artifacts, or moving Airflow Bundle references.

**Ownership boundary**: Jenkins pipeline and validation configuration in the final target repository layout.

**In scope**:

- Integrate the existing Python compilation and test checks, adjusting paths only as needed for the target repository.
- Keep CI validation-only and ensure it has no Bundle publication/ref-update behavior.
- Preserve the approved Jenkins Docker socket mount per requirements and record that the current CI commands do not use it.

**Stories**: US-05; cross-cutting support for US-02's Compose integration acceptance.

**Dependencies**: Final source paths and validation commands from Units 1–3.

**Exit contract**: Jenkins validation configuration is reviewable and passes its applicable CI checks; no deployment or Bundle mutation occurs.

**Out of scope**: Deployment, image publication, Bundle release, or Docker lifecycle orchestration.

## Completion

Units are ready for the per-unit Construction loop after this decomposition and its dependency/story maps receive explicit approval. Functional/NFR/Infrastructure design will specify detailed implementation and test behavior per unit. No canonical knowledge files are updated during this stage; the approved execution plan defers durable knowledge updates until intent closure.
