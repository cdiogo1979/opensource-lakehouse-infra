# Infrastructure Design — Unit 2 StarRocks Runtime

## Design Summary

Add StarRocks FE and BE as opt-in services in the existing Docker Compose project. The design keeps the approved one-FE/one-BE topology, preserves the shared lakehouse services and data, and uses a one-shot Compose preflight to gate both nodes on paired persistent-state checks.

## Decisions

| Area | Infrastructure mapping |
|---|---|
| Deployment | Existing local Compose project; FE, BE, and preflight use the `starrocks` profile. Default `docker compose up` continues to start the existing platform without StarRocks. |
| Release | Candidate release is StarRocks 4.1.6, the current 4.1 patch shown by the official release notes and official FE/BE image tags checked on 2026-10-24. FE and BE use matching 4.1.6 Ubuntu images. The 4.1.0 container startup issue is fixed in later 4.1 releases. |
| Image pinning | Pin upstream base images by immutable multi-platform index digest: `starrocks/fe-ubuntu:4.1.6@sha256:d07aa750be77625a09866a76dbfe0ee032baeb5e48fe0e952d30cb525329dc31` and `starrocks/be-ubuntu:4.1.6@sha256:bf0f5ca7fd9fc4e568d4d0e593e362f229b376976b513a5a549b1b922d9ec23b`. Local derived images add the Kerberos client and cron. No moving `latest` tag is used. Record the resulting local image digests during build/verification. |
| Compute | One FE and one BE, no replicas or autoscaling. Keep settings in Compose. Do not set speculative hard CPU/memory limits; later integrated verification records observed minimum/recommended resources and conditions. |
| FE process | FE container uses the official FE startup script and stable Compose hostname `starrocks-fe`, configured for FQDN host identity. FE metadata persists at `/opt/starrocks/fe/meta`. |
| BE process | BE starts after FE SQL readiness, registers with the FE using an idempotent startup check, and starts the official BE process. BE storage persists at `/opt/starrocks/be/storage`. |
| Ticket refresh | Derived FE/BE images add Kerberos client utilities and cron. Each container obtains a TGT before starting StarRocks, then refreshes hourly with its own read-only keytab and private cache. `KRB5CCNAME` points inside a per-container memory-backed `/run/krb5` tmpfs with restrictive permissions. The current KDC maximum ticket lifetime is 10 hours, so hourly refresh leaves retry margin. A failed refresh logs only a safe status; it does not stop an otherwise running FE/BE while its current ticket remains valid. |
| JVM Kerberos config | Mount `infra/kerberos/krb5.conf` read-only at `/etc/krb5.conf`; set `JAVA_OPTS=-Djava.security.krb5.conf=/etc/krb5.conf` in the FE and BE config using release-supported configuration. |
| Hive Kerberos client config | Mount minimal, credential-free `core-site.xml` and `hive-site.xml` into FE and BE configuration directories. Set Hadoop authentication to Kerberos before UGI initializes, enable Hive Metastore SASL, and name the provisioned Hive service principal explicitly. Do not mount the full Hive configuration because it contains unrelated database and RustFS credentials. |
| Credential mounts | Mount `.runtime/credentials/keytabs/starrocks.keytab` read-only into each node. Mount the file-backed Compose secret `rustfs-starrocks-secret-key` read-only at `/run/secrets/rustfs-starrocks-secret-key`; the stable RustFS access-key ID is `starrocks`. Do not copy the secret into tracked config or logs. The catalog/bootstrap unit will consume the credential through a release-supported mechanism. |
| State validation | A one-shot `starrocks-preflight` Compose service in the same profile mounts only the FE metadata and BE storage volumes read-only. It inspects both paths as a pair and exits successfully only for either a clean paired-empty first start or a paired existing state. A one-sided empty/missing state fails closed with a safe diagnostic. Invalid content is preserved; native FE/BE startup and health checks must also fail without deleting state. FE and BE depend on `service_completed_successfully`. The preflight never initializes StarRocks directories or writes a marker. A documented host wrapper runs a fresh preflight before each StarRocks start, then starts FE/BE; it removes only an earlier successful preflight container, while retaining a failed one for inspection. |
| Persistent storage | Create new Compose-managed named volumes `starrocks-fe-meta` and `starrocks-be-storage`. Keep them separate and preserve them through normal stop, restart, and recreate operations. No cleanup/reset command is added to routine workflows. |
| Network | Attach StarRocks nodes to existing `iceberg_net` and use Compose service DNS. KDC is a healthy startup dependency. Hive Metastore and RustFS are not FE/BE process-readiness dependencies; catalog availability is tested in Unit 3. |
| Host endpoints | Publish FE UI `8030` and SQL `9030` on `127.0.0.1` only. FE edit-log/RPC and BE RPC/heartbeat/HTTP/bRPC/Starlet ports remain internal to `iceberg_net` and are not published. |
| Health/readiness | FE health uses its unauthenticated `/api/health` endpoint because the SQL root account is password-protected after bootstrap. BE health checks its service port; the host startup wrapper uses the protected root credential to register and verify the BE through SQL. Runtime readiness does not claim Hive catalog or RustFS query readiness. |
| Restart/recovery | FE and BE use the approved process-exit restart policy. A live but unhealthy process is reported not ready for operator action. Compose restart/recreate never removes the two StarRocks volumes. |
| Observability | Use container stdout/stderr, health status, and Docker Compose logs. No persistent monitor, alerting, dashboard, log collector, message queue, load balancer, or API gateway is added. |

## Startup and Recovery Flow

1. Operator invokes the StarRocks startup wrapper. It targets only the StarRocks profile and leaves existing services and state intact.
2. The wrapper preserves a failed prior preflight for inspection; otherwise it removes only the prior successful preflight container, then runs a fresh `starrocks-preflight` against the two new named volumes.
3. If both data paths are empty, preflight permits first startup. If both contain existing state, it permits node startup; a one-sided empty path or unreadable/inconsistent layout fails closed. Preflight is read-only and emits no contents or credentials.
4. After successful preflight, the wrapper starts FE and BE. Compose's successful-completion dependency also prevents either node from starting before coordinator success.
5. FE obtains its initial TGT, starts cron, and runs the StarRocks FE process. The FE SQL health check must pass.
6. BE obtains its initial TGT, confirms the FE is available, idempotently registers itself if absent, and starts the StarRocks BE process.
7. Runtime readiness is true only when FE SQL and both FE/BE liveness checks pass. Hive Catalog and RustFS compatibility is a separate Unit 3/integrated verification gate.
8. On process exit, Compose applies the approved restart policy. On persistent unhealthy state, the operator investigates while the state volumes remain intact.

## Compatibility and Verification Boundary

StarRocks documentation supports Hive catalogs backed by Hive Metastore and S3-compatible storage, and directs operators to obtain a TGT on each FE/BE and refresh it periodically with cron. The official Docker Compose Iceberg example uses separate Ubuntu FE/BE images and identifies the SQL/UI ports. The release notes document a BE container startup issue in 4.1.0 and its fix in 4.1.1; the selected 4.1.6 candidate is later in the same line.

The documentation does not certify this exact Hive Metastore 3.1.3, Kerberos, Iceberg, and RustFS combination. Unit 3 and integrated Build and Test must prove the selected image works with this stack before the integration is declared complete. FE/BE state-marker detection, cron startup, exact config injection, host architecture, and the resulting derived-image digests are implementation verification items. Any ambiguity in detecting safe paired state must fail closed rather than trigger reinitialization.

## Sources Checked 2026-10-24

- [StarRocks 4.1 release notes](https://docs.starrocks.io/releasenotes/release-4.1/) — 4.1.6 release and the 4.1.0 container issue/fix note.
- [Official FE 4.1.6 multi-platform image manifest](https://hub.docker.com/layers/starrocks/fe-ubuntu/4.1.6/images/sha256-9339bd7107c437858484b17282e27ce135745064bc534c04130c2bf40de0f3d9).
- [Official BE 4.1.6 multi-platform image manifest](https://hub.docker.com/layers/starrocks/be-ubuntu/4.1.6/images/sha256-dee905b77a275fc5996084e4f48d6c9488e00b7d90342cf3b05192ad155ce76c).
- [StarRocks Hive Catalog and Kerberos guidance](https://docs.starrocks.io/docs/data_source/catalog/hive_catalog/) — Hive Metastore/S3-compatible storage, per-node `kinit -kt`, periodic cron refresh, and Java Kerberos configuration.
- [StarRocks Iceberg Docker Compose guide](https://docs.starrocks.io/docs/quick_start/iceberg/) — separate FE/BE Ubuntu images and FE UI/SQL endpoints.
- [Docker Compose startup dependency conditions](https://docs.docker.com/compose/how-tos/startup-order/) — `service_healthy` and `service_completed_successfully` behavior.

## Category Applicability

- **Deployment environment:** Local Compose only; no cloud, production, or Kubernetes target.
- **Compute:** Single FE and BE; no scaling subsystem; resource guidance is measured later.
- **Storage:** Two new persistent StarRocks volumes; no change to existing shared volumes.
- **Messaging:** Not applicable; no asynchronous work or queue.
- **Networking:** Existing internal Compose network and loopback-only FE host endpoints; no gateway/load balancer.
- **Monitoring:** Compose health and logs only; no new observability service.
- **Shared infrastructure:** Existing KDC/HMS/RustFS and network are reused without modifying their state or credentials.
