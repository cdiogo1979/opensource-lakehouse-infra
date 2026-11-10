# Unit 1 Infrastructure Design Plan — Identity Provisioning

## Unit Context

Unit 1 extends the existing local Docker Compose identity-provisioning workflow with StarRocks Kerberos and RustFS identities. The approved design retains the current Bash/Python provisioner, invokes both provider branches independently, stores protected local credentials under ignored `.runtime/credentials/`, and introduces no persistent or background service.

The current `identity-provisioner` profile service shares the `iceberg_net` network, waits for the KDC, Hive Metastore, and bucket initialization, receives admin/provider credentials as Compose secrets, mounts the Kerberos bootstrap keytab read-only, and mounts the keytab output directory and status directory. The host wrapper runs this service and then renders/restarts Hive configuration.

## Infrastructure Design Tasks

- [x] Map identity-provisioning responsibilities to the existing Compose service, network, secret sources, and bind mounts.
- [x] Resolve deployment target and whether identity provisioning remains in the current local Compose profile.
- [x] Resolve compute/service reuse and lifecycle dependencies for the StarRocks identity additions.
- [x] Resolve host/container credential storage and mount permissions for the StarRocks keytab and RustFS secret.
- [x] Resolve network, monitoring, and shared-resource requirements; record non-applicable categories with rationale.
- [x] Check answers for completeness and ambiguity; create clarification questions if needed.
- [x] Generate `construction/unit-1-identity-provisioning/infrastructure-design/infrastructure-design.md` and `deployment-architecture.md`.
- [x] Validate consistency with Functional/NFR Design and present the artifacts for explicit approval.
- [x] Record user approval and advance to Unit 1 Code Generation Planning.

## Questions

Fill each `[Answer]:` line with an option letter. Choose the last option, `Other`, and describe your choice if none of the listed options fits.

### Question 1 — Deployment environment

Where should Unit 1 identity provisioning run?

A) Keep it in the existing local Docker Compose `identity-provisioning` profile and the existing `scripts/provision-identities.sh` host wrapper.

B) Move identity provisioning to a host-only script that directly contacts KDC and RustFS, without running the Compose provisioner.

C) Add a separately deployed identity-provisioning environment or orchestrator.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

### Question 2 — Compute and lifecycle dependencies

How should the StarRocks identity tasks use compute and service dependencies?

A) Reuse the existing one-shot `identity-provisioner` container; retain its current KDC, Hive Metastore, and bucket readiness dependencies, then keep the host wrapper's existing Hive config render/restart sequence.

B) Split StarRocks identity provisioning into a separate one-shot Compose service with only KDC and RustFS dependencies.

C) Run the StarRocks identity steps inside the future StarRocks FE container at startup.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

### Question 3 — StarRocks credential storage and mounts

How should the new StarRocks identity material be made available to the provisioner and future StarRocks runtime?

A) Keep host files in ignored `.runtime/credentials/`; provide the RustFS secret through a Compose file-backed secret and the keytab through the existing keytabs bind mount, read/write only where provisioning requires it and read-only for the runtime consumer.

B) Store both items in a dedicated named Docker volume managed by the provisioning container.

C) Keep both items only inside the container filesystem and regenerate them whenever the container runs.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

### Question 4 — Networking

What network connectivity should the identity-provisioning infrastructure use?

A) Reuse the existing internal `iceberg_net`; provisioner-to-KDC and provisioner-to-RustFS traffic uses Compose service DNS, with no new host-published ports.

B) Add a dedicated identity-provisioning network with explicit connections to KDC and RustFS.

C) Publish KDC or RustFS administration endpoints on the host for the provisioner to use.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

### Question 5 — Storage lifecycle and preservation

How should infrastructure changes handle existing identity data and shared state?

A) Add only the StarRocks credential/secret references and keytab output needed by this unit; retain existing keytabs, local credential files, KDC data, RustFS accounts/policies, database state, and all shared volumes.

B) Recreate the identity-provisioner container and its ephemeral state while preserving all named shared volumes and existing host credentials.

C) Replace existing shared identity storage with a new StarRocks-specific volume layout.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

### Question 6 — Monitoring and operations

What infrastructure-level monitoring or log collection should Unit 1 add?

A) Add none; this remains a manually invoked one-shot operation with redacted status emitted to the invoking terminal. Existing Compose service logs remain available for runtime troubleshooting.

B) Add a persistent local audit output file with provider outcomes, excluding secrets.

C) Add a monitoring/alerting service for identity provisioning.

D) Other (please describe after `[Answer]:` below)

[Answer]:A

## Applicability Notes

- Cloud-provider selection is not applicable to this local Docker Compose PoC; Question 1 confirms the deployment target.
- Compute sizing/autoscaling is not applicable to a short-lived one-shot provisioner; Question 2 covers service reuse and dependencies.
- Storage infrastructure means local credential files, Compose secret sources, and keytab mounts; there is no new application database or data lifecycle.
- Messaging/queuing is not applicable because the approved design has no background work or persistent recovery queue.
- Network design is limited to existing Compose-internal service connectivity; no load balancer/API gateway is required.
- Monitoring is limited by approved NFR requirements to operator-visible redacted results; Question 6 confirms whether any local audit artifact is desired.
- Shared infrastructure must preserve the existing KDC, Hive, RustFS, volumes, identities, and provisioning flow unless explicitly changed by an answer.
- No application or runtime configuration is changed during Infrastructure Design planning.
