# Infrastructure Design — Unit 1 Identity Provisioning

## Infrastructure Scope

Extend the existing local Docker Compose identity-provisioning path with the StarRocks Kerberos principal/keytab and RustFS identity secret/policy. Reuse the current one-shot `identity-provisioner` profile service and `scripts/provision-identities.sh` host wrapper. No new service, host-published port, persistent volume, monitoring system, queue, or application database is introduced.

## Deployment Mapping

| Logical responsibility | Infrastructure mapping |
|---|---|
| Operator entry point | Host command `scripts/provision-identities.sh`; it builds/runs the Compose identity-provisioner and, after successful provisioning, renders and restarts Hive configuration as it does today. |
| Provisioning compute | Existing one-shot `identity-provisioner` service in Compose profile `identity-provisioning`. |
| Kerberos provider | Existing `kdc` service on `iceberg_net`, with current health dependency. |
| RustFS provider | Existing object-store service reachable through the Compose network; bucket initialization remains a successful-completion dependency. |
| Hive integration boundary | Existing healthy `hive-metastore` dependency and post-provision host-side config render/restart behavior are retained. |
| RustFS credential source | Add a file-backed Compose secret referencing the ignored host file `.runtime/credentials/rustfs-starrocks-secret-key`; the access-key ID remains the approved stable identity `starrocks`. |
| Kerberos keytab output | Create `.runtime/credentials/keytabs/starrocks.keytab` through the existing keytabs bind mount, writable to the provisioning service. The future StarRocks runtime consumes this exact keytab read-only. |
| Network | Existing internal `iceberg_net`, with Compose service DNS for provider communication. No new host-published port. |
| Result delivery | Redacted provider outcomes and aggregate status to the invoking operator; no persistent log or monitoring component. |

## Compose Changes Required During Code Generation

1. Add `rustfs-starrocks-secret-key` to the Compose file-backed `secrets` map, pointing to `.runtime/credentials/rustfs-starrocks-secret-key`.
2. Grant that secret to the existing `identity-provisioner` service. The StarRocks account access-key ID remains the fixed approved name and does not need to be stored as secret material.
3. Reuse the current keytabs bind mount for the StarRocks keytab file. Ensure the provisioning script creates/uses the StarRocks path with the approved owner-only mode and does not overwrite an existing keytab.
4. When Unit 2 adds the StarRocks service, mount the same keytab and RustFS secret read-only into the runtime at explicitly documented paths. Unit 1 does not add that service or its mounts.
5. Preserve the existing `identity-provisioner` profile, dependencies, `iceberg_net`, all current secrets and mounts, KDC data, database state, and shared volumes.

## Credential Protection

- The host credential files remain under ignored `.runtime/credentials/` paths.
- Credential directories use mode `0700`; StarRocks secret and keytab files use mode `0600`.
- Compose file-backed secrets are consumed through their mounted secret paths. Secret values are not placed in Compose environment variables or command-line arguments.
- The existing keytab directory mount is available to the provisioner for keytab creation. Only the StarRocks keytab is mounted read-only into the future runtime service.
- Provisioning may correct permission bits without changing credential contents. If expected ownership or protected modes cannot be established, provisioning fails with a redacted operator diagnostic.
- No new credentials or existing principal keys are implicitly rotated.

## Dependency and Invocation Behavior

1. The operator runs `scripts/bootstrap-local.sh` when the protected local credential files have not yet been initialized.
2. The operator runs `scripts/provision-identities.sh`.
3. Compose ensures KDC and Hive are healthy and bucket initialization completed before the one-shot provisioner runs.
4. The provisioner attempts Kerberos and RustFS branches independently once, emits both safe outcomes, and returns aggregate failure if either branch fails.
5. On successful full provisioning, the host wrapper renders Hive configuration and restarts/waits for the Metastore using the existing behavior. If the provisioner fails, the host wrapper exits without applying this success-only follow-up.
6. The operator corrects the issue and invokes the command again; existing state is inspected and reused idempotently.

## Non-Applicable Infrastructure

- **Cloud provider:** Not applicable; this unit targets the existing local Docker Compose environment.
- **Compute sizing/autoscaling:** Not applicable to a short-lived one-shot identity provisioner; no service scaling is required.
- **Messaging/queue:** Not applicable; provisioning is synchronous and operator-triggered.
- **Load balancer/API gateway:** Not applicable; no new externally reachable endpoint is introduced.
- **Monitoring/alerting:** Not applicable under the approved requirements; output is delivered to the invoking terminal and existing Compose logs remain available.
- **New persistent storage:** Not applicable; use existing host credential directory and keytab bind mount, with no new volume.

## Preservation Constraints

Do not remove or recreate existing KDC data, Hive Metastore/PostgreSQL state, RustFS objects/accounts, existing keytabs, credential files, Compose services, or named volumes. Unit 1 adds only StarRocks credential references and the StarRocks identity resources. Airflow/Jenkins remains out of scope.
