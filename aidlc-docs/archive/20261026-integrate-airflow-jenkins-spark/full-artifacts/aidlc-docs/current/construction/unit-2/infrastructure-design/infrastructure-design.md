# Infrastructure Design — Unit 2 Airflow Bundle Runner

## Purpose and Deployment Scope

Integrate Airflow 3 and Jenkins into the target local Docker Compose project while retaining the existing lakehouse services, network, credential files, and persistent data. Airflow uses Git DAG Bundles and Docker-created Spark run containers. Each active run creates one driver and one worker-only container using the local derived Spark 3.5.5 image. Both containers use separate private Kerberos caches and the existing read-only writer credential files; the worker registers with the shared Spark master and may host executors from any active application.

The user selected all-interface host publication for the Airflow UI (`8085:8080`) and Jenkins UI (`8098:8080`). The Jenkins inbound-agent port is not published. These UIs are reachable from other hosts that can route to this machine and are allowed by host/network firewalls. Compose does not terminate TLS in this design. Keep application authentication configured; production-grade remote access/TLS is outside the local PoC scope.

## Compose Service Mapping

| Service | Infrastructure responsibilities | Network / host exposure / persistent state |
|---|---|---|
| `airflow-postgres` | Airflow-only metadata database, health checked before initialization | `iceberg_net`; private Compose service port; dedicated `airflow-postgres-data` volume, separate from Hive metastore PostgreSQL |
| `airflow-init` | Run Airflow database migrations and configured bootstrap once PostgreSQL is healthy | `iceberg_net`; exits after successful initialization |
| `airflow-api-server` | Serve Airflow UI/API; no Docker socket or writer credential mounts | `iceberg_net`; publish `8085:8080` on all host interfaces |
| `airflow-scheduler` | LocalExecutor scheduler and run coordinator; admit up to two active DAG runs; create/remove driver and worker through Docker Engine | `iceberg_net`; Docker socket; same host-visible Bundle directory and run credential source paths; no UI host port |
| `airflow-dag-processor` | Fetch, resolve, and parse configured Git Bundles at pinned revisions | `iceberg_net`; read/write host-visible Bundle storage; no Docker socket or writer credentials |
| `airflow-triggerer` | Retain the Airflow 3 service topology for deferrable task support | `iceberg_net`; no Docker socket or writer credentials |
| `jenkins` | Run repository validation only; no Bundle publishing or reference updates | `iceberg_net`; Docker socket retained by approved baseline; publish `8098:8080` on all host interfaces; persistent `jenkins-home` volume; no inbound-agent host port |
| Existing lakehouse services | Continue providing Spark, KDC, Hive Metastore, PostgreSQL, RustFS, JupyterHub, TPCH tooling, and StarRocks | Existing service names, ports, credentials, configs, network membership, and named data volumes are preserved |

Compose services use the existing network key `iceberg_net`, whose Docker network name is `iceberg-poc-net`. Containers created directly by the scheduler must explicitly join `iceberg-poc-net`; Compose service DNS resolves the Spark master as `spark` on port `7077`.

## Airflow Configuration and Bundle Storage

- Preserve the inspected Airflow 3 LocalExecutor and Git Bundle model: API server, scheduler, DAG processor, triggerer, initializer, and a distinct PostgreSQL service.
- The DAG processor and scheduler mount one host-visible Bundle storage directory at the same absolute path. Use ignored runtime state under the project root, for example `${PROJECT_ROOT}/.runtime/airflow-dag-bundles`; do not treat the sibling project's generated `.airflow-dag-bundles` checkout/cache as maintained source.
- The scheduler passes the exact pinned Bundle revision path to Docker as a read-only host bind mount in the driver. Validate that the host Docker daemon can resolve the source path; container-only paths are insufficient for Docker API bind sources.
- Bundle repository URL, Git connection, and tracking references are deployment configuration. Only the dev environment is configured for this local lakehouse. Leave UAT/prod endpoints unset and fail closed; never redirect them to dev.
- The scheduler owns the Docker socket because LocalExecutor runs Docker lifecycle tasks there. The API server, DAG processor, triggerer, and initializer do not receive the Docker socket.
- Keep Airflow API/admin and database credentials in the existing Airflow secret/connection mechanism. Do not pass writer secret values as ordinary environment variables or put credentials in Bundle content.

## Run-Scoped Driver and Worker Container Contract

For each admitted Airflow DAG run, create exactly one driver and one worker-only container from `local/spark-iceberg:3.5.5_1.8.1-krb5`. Include a stable run identifier in container names/labels so cleanup can identify only that pair. Enforce the two-active-run cap before either container is created; queue further runs in Airflow.

| Concern | Driver | Worker-only container |
|---|---|---|
| Image and network | Approved local derived Spark image; `iceberg-poc-net` | Same image; `iceberg-poc-net` |
| Bundle | Exact run-pinned host path mounted read-only | No Bundle mount unless the worker process needs configuration files; avoid copying workload source into it |
| Kerberos | Read-only writer keytab and `/etc/krb5.conf`; private `/run/krb5` tmpfs | Same read-only credential inputs; independent private `/run/krb5` tmpfs |
| RustFS | Read-only writer access/secret files mounted from host credential paths | Same read-only file mounts for executors scheduled on this worker |
| Readiness | Valid writer TGT plus Spark master connectivity before submission | Valid separate writer TGT, worker process readiness, and registration at `spark://spark:7077` |
| Spark role | Spark client/driver submitting in remote mode | Worker-only startup mode; no master/history/notebook process |
| Lifecycle | Stop when submissions/tasks settle; remove on all outcomes | Decommission on cleanup, drain within shared 60-second cleanup deadline, then stop/remove |

Each container creates its own private ticket cache on ephemeral tmpfs with owner-only access. Caches are not shared between the pair, concurrent runs, Airflow, the long-lived Spark worker, or notebooks. Keytab and RustFS secret files are read-only; host files retain restrictive modes. The scheduler itself receives credential file paths only where required to create bind mounts, not secret values.

Airflow waits up to five minutes from container creation for both readiness conditions, polling at least every five seconds. It must not submit workload code until both are ready. A startup/readiness failure enters paired cleanup and remains a failed run.

## Worker Decommission and Cleanup

At cleanup, stop the driver and request worker decommission immediately. The Spark master must no longer assign new executors to that worker. Within the same 60-second paired-cleanup budget, observe whether executors from other active applications leave the worker. If it drains, stop/remove the worker. If foreign executors remain at the deadline, stop/remove it and emit a sanitized `worker_drain_timeout` diagnostic. That forced removal may interrupt another application, which may retry or fail. Record the cleanup diagnostic separately and preserve the original workload result.

Cleanup is idempotent and limited to run-labeled containers and ephemeral runtime state. It does not stop the shared master or long-lived worker and does not delete tables, catalog metadata, RustFS objects, Bundle revisions, or persistent named volumes. If a container is already absent, consider that container cleaned. If Docker removal fails, report cleanup failure without masking the workload outcome.

The exact decommission command and a reliable way to attribute/observe executors on an individual worker are not assumed by this design. Unit 2 Code Generation must choose a mechanism compatible with the pinned Spark image; integrated Build and Test must prove it. A script's presence alone is not evidence that the shared master stops assignments or that the intended drain is observable.

## Service Dependencies and Startup

1. `airflow-postgres` becomes healthy.
2. `airflow-init` completes migrations and bootstrap successfully.
3. Airflow API server, scheduler, DAG processor, and triggerer start after successful initialization. Airflow remains operable if a lakehouse service is temporarily unavailable; individual runs fail closed on Spark, Kerberos, metastore, or object-store readiness problems.
4. Jenkins starts independently with its persistent home. Jenkins validates repository changes only and does not deploy or move Bundle refs.
5. The existing Spark service retains its Unit 1 dependencies on healthy KDC, RustFS, bucket initialization, and Hive Metastore. Run containers join the same Docker network and wait for their own TGT/worker readiness before submission.

No Airflow service shares the Hive metastore PostgreSQL database or its volume. Airflow startup does not initialize or reset lakehouse data.

## Storage and Volume Ownership

- Add distinct named volumes for Airflow metadata PostgreSQL, Airflow logs if required by the selected Airflow image topology, and Jenkins home.
- Keep the Bundle checkout in ignored project runtime state, not a named data volume and not a source-controlled artifact.
- Preserve every existing Hive, metastore DB, KDC, RustFS, JupyterHub, and StarRocks volume and its contents. Never use volume reset/removal commands as part of this integration.
- Keep all writer credential sources under the existing `.runtime/credentials` host tree with read-only mounts into the driver/worker. Do not copy them into Airflow images, Jenkins, the Bundle checkout, or persistent data volumes.

## Networking and Host Exposure

- Attach integrated Compose services to `iceberg_net` (Docker name `iceberg-poc-net`) where they need peer connectivity.
- Attach per-run driver and worker containers to `iceberg-poc-net` through the Docker API.
- Spark URL: `spark://spark:7077`. Hive Metastore: `thrift://hive-metastore:9083`. RustFS S3 endpoint: `http://object-store:9000`. Verify these names from all required containers at runtime.
- Publish Airflow UI/API as `8085:8080` and Jenkins UI as `8098:8080` with no host IP, which binds to all host interfaces. Do not publish Jenkins agent port `50000` absent a separate requirement.
- Do not add host publications for Airflow PostgreSQL, Hive Metastore, Spark worker ports, Kerberos, or RustFS beyond the current Compose bindings.
- All-interface HTTP publication is an explicit local deployment choice. TLS termination is not included; host/network firewall and application authentication govern access.

## Monitoring and Applicable Infrastructure Categories

- **Health/readiness**: Airflow service health checks cover process/API and metadata DB readiness. Per-run driver/worker readiness is run-scoped and evaluated by the scheduler before submission. Docker health alone does not prove a valid TGT or worker registration.
- **Logging**: Airflow task logs record run ID, pinned revision, environment, phase, and sanitized errors. Never log keytab/S3 values, ticket contents, raw credential-bearing output, or secret-bearing command arguments.
- **Messaging**: No broker or new queue is introduced. Airflow's existing queue/concurrency controls gate run-container creation; Spark Standalone schedules executors.
- **Compute**: Reuse the local Spark image and current long-lived resource settings. No new performance/capacity claim is made.
- **Monitoring/alerting**: Existing Airflow state and Compose health/log surfaces only; no external observability stack is added.

## Verification Items for Build and Test

- Validate Compose service dependency ordering and that Airflow metadata/Jenkins volumes are separate from all lakehouse data.
- Verify both UIs bind to all host interfaces at the selected ports and the Jenkins agent port is not published.
- Verify only the Airflow scheduler and approved Jenkins service receive the Docker socket.
- Verify host-visible Bundle/credential bind paths resolve through the Docker daemon, with Bundle/keytab/secret mounts read-only where required.
- Verify driver and worker join `iceberg-poc-net`, resolve `spark`, and connect to `spark://spark:7077`.
- Verify two active runs maximum, separate private TGT caches, five-minute paired readiness, and paired cleanup.
- Verify decommission stops new executor assignments, drain observation works, and timeout removal/reporting occurs within the shared 60-second cleanup budget. Record any cross-run impact.
- Verify UAT/prod remain unavailable and do not fall back to dev.
- Verify all three Hive catalogs, Spark catalog addressing, StarRocks query path, and RustFS prefix permissions under the matrix in ABR-NFR-06/07.

These are later integration verification targets. Infrastructure Design does not claim they have been tested.
