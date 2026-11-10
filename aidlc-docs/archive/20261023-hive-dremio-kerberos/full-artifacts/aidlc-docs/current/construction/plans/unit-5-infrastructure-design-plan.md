# Infrastructure Design Plan — Unit 5 JupyterHub and Per-User Spark

## Scope

Map the approved JupyterHub, DockerSpawner, and isolated single-user Spark components onto the existing `hive-dremio-rustfs` Docker Compose project. Reuse its `iceberg-poc-net` network and current KDC, Hive Metastore, and RustFS services. Add only the Hub and image-building/session infrastructure required by the approved design; preserve local-only exposure, three concurrent user containers, matching credentials, and separate persistent workspaces.

This stage defines infrastructure mapping only. It does not modify Compose or image files, copy sibling project files, create credentials, start services, or run tests.

## Baseline Reviewed

- The target Compose network is named `iceberg-poc-net`; Hive, KDC, RustFS, and Spark services already use it.
- Existing host-published services bind to `127.0.0.1`. Host ports 8008 is not currently published in this Compose file.
- The target project has `user_a`, `user_b`, and `admin` Kerberos keytabs and distinct RustFS credential files in `.runtime/credentials/`; secret values were not read.
- The sibling JupyterHub Compose file binds port 8008 without a loopback host IP, uses its own Hub volume, mounts the Docker socket, and currently has a shared writable notebooks bind mount.
- The sibling Hub uses DummyAuthenticator/DockerSpawner. Its single-user image runs as `jovyan`; its Spark configuration must consume the target Hive catalog and per-user identity contract.
- Approved NFR design requires the Docker socket only in Hub, local defaults, no queue/monitoring component, per-user workspaces, and manual recovery.

## Infrastructure Categories

| Category | Applicability | Mapping focus |
|---|---|---|
| Deployment environment | Applicable | Integrate with the existing Compose project; determine default/profile lifecycle and image-build entry point. |
| Compute | Applicable | One Hub container and up to three DockerSpawner user containers on the local Docker host. |
| Storage | Applicable | Hub state, distinct user workspaces, read-only credential mounts, and existing platform volumes. |
| Messaging | Not required by approved NFR design | Synchronous DockerSpawner calls; confirm no queue or broker is added. |
| Networking | Applicable | Loopback-only Hub port and user-container connectivity to `iceberg-poc-net` service DNS. |
| Monitoring | Applicable at local operational level | Use container state/logs; determine whether a Compose-native Hub healthcheck is useful without a new service. |
| Shared infrastructure | Applicable | Keep credentials, keytabs, ticket caches, writable volumes, and Docker socket access separated by role/username. |

## Design Checklist

- [x] Resolve lifecycle/profile, image build, workspace storage, credential delivery, network, queue, and health-visibility questions in `unit-5-infrastructure-design-questions.md` (A/A/A/A/A/A/A).
- [x] Map Hub and user containers to the existing Compose services/network and loopback port.
- [x] Define per-user volume and read-only credential mount sources without exposing secrets to unrelated services.
- [x] Map image build and startup dependencies, including KDC/Hive/RustFS readiness expectations.
- [x] Define lifecycle, failure visibility, preserved-volume behavior, and non-destructive recovery boundaries.
- [x] Create `construction/unit-5-jupyter/infrastructure-design/infrastructure-design.md` and `deployment-architecture.md`.
- [x] Update workflow state and audit trail; present the design for explicit review before Code Generation.

## Questions and Approval

Answers were validated as A/A/A/A/A/A/A: include Hub in default Compose startup; use an explicit Compose build target for the single-user image; use separate named work volumes; mount only matching credential files read-only into spawned sessions; attach Hub and sessions to the existing `iceberg-poc-net` and publish Hub on loopback port 8008; keep synchronous spawn with no queue; and use existing Docker status/logs without an added healthcheck. Question 6 was left blank in the response file and was filled from the explicit no-queue answer already approved in Unit 5 NFR Design. The infrastructure artifacts are ready for review and explicit approval.
