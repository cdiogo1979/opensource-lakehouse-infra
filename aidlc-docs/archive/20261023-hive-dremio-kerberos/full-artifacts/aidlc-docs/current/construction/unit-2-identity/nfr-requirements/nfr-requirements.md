# Unit 2 Identity Provisioning — NFR Requirements

## Scope and Operating Context

These requirements apply to the one-shot identity/permission provisioner and its local component setup operations for the single-host Docker Compose PoC. The fixed identity set is `admin`, `write-service-account`, `user_a`, `user_b`, and the existing Hive Metastore service principal. This is not a production identity service and has no external identity provider.

## Capacity and Scalability

- **U2-NFR-01**: Support the fixed PoC principals and component accounts on one local Compose host.
- **U2-NFR-02**: Bulk identity import, concurrent provisioning, horizontal scaling, and multi-host operation are not acceptance requirements.
- **U2-NFR-03**: If a selected component cannot represent the fixed identity set or required account mappings, report the capability gap; do not silently omit an identity.

## Performance

- **U2-NFR-04**: Prioritize correctness, safe repeatability, and observable per-component results over provisioning speed.
- **U2-NFR-05**: No setup-time, latency, or throughput SLA is required. Provisioning may be sequential to preserve dependency ordering.

## Availability and Recovery

- **U2-NFR-06**: Provisioning is a single-host best-effort operator workflow. No HA, failover, uptime target, or automated disaster recovery is required.
- **U2-NFR-07**: A normal rerun preserves existing principals, accounts, credential material, grants, and persistent data unless an explicit rotation or reset operation is requested.
- **U2-NFR-08**: Credential rotation is explicit and coordinated with all dependent components. Automatic rotation on ordinary provisioning runs is prohibited.
- **U2-NFR-09**: Partial failure preserves prior successful setup for diagnosis and safe rerun. The provisioner does not automatically delete principals, accounts, keytabs, policies, database records, or data.

## Security and Exposure

- **U2-NFR-10**: Kerberos credentials and each component's native credentials are distinct. Administrator credentials are separate from `write-service-account` and test-user credentials; component-native admin credentials are separately generated for each component.
- **U2-NFR-11**: Generated keytabs, passwords, RustFS access keys/secrets, and native credentials remain in ignored, host-restricted local runtime storage. They are not committed, embedded in images, or placed in tracked examples.
- **U2-NFR-12**: Mount credentials only into the component that needs them and read-only where supported. Do not expose the Hive Metastore PostgreSQL credential to the ETL writer.
- **U2-NFR-13**: Logs, status output, and error diagnostics may show principal/account names, component names, operation status, and redacted failure context. They must never show passwords, secret keys, keytab contents, or ticket-cache contents.
- **U2-NFR-14**: Keep published endpoints loopback-only and component setup traffic inside the private Compose network. No LAN exposure is added by the provisioner.
- **U2-NFR-15**: Do not grant `write-service-account` platform-administrator permissions. Its Hive and RustFS permissions must be limited to approved database/table creation and warehouse writes, subject to component feasibility.
- **U2-NFR-16**: Do not claim production security. The KDC and test identities are disposable local development mechanisms.

## Technology Compatibility

- **U2-NFR-17**: Preserve existing Hive 3.1.3, Spark 3.5.5/Iceberg 1.8.1, Dremio Community 26.0.5, PostgreSQL 16.14, and RustFS 1.0.0-glibc pins while compatible.
- **U2-NFR-18**: Any version change, new runtime identity service, credential-boundary relaxation, or broader permission required to provision an account must be documented and reviewed before implementation.
- **U2-NFR-19**: Use supported component-owned setup interfaces. If a required account or permission cannot be created with the pinned component, mark that requirement blocked and provide the smallest proposed adjustment for review.
- **U2-NFR-20**: A successful account-provisioning operation does not certify Hive/RustFS authorization or effective-user propagation. Those remain explicit integration gates.

## Reliability and Observability

- **U2-NFR-21**: Do not begin mutation until required component readiness and protected credential storage are validated.
- **U2-NFR-22**: Retry only bounded dependency-availability checks and operations known to be idempotent. Authentication, authorization, configuration, and unsupported-capability failures stop promptly.
- **U2-NFR-23**: Stop at the first failed required account or permission operation. Report the overall run as incomplete/failed even if earlier component setup succeeded.
- **U2-NFR-24**: Per-identity/component output identifies `created`, `already-present`, `deferred`, or `failed` state without disclosing credential values.
- **U2-NFR-25**: Reader grants are reported as deferred until Unit 3 creates `databaseA` and `databaseB`; they are not reported as configured or verified before then.
- **U2-NFR-26**: No monitoring or alerting stack is required. Compose status and actionable local logs are sufficient.

## Maintainability and Usability

- **U2-NFR-27**: Keep component setup actions separate behind small, reviewable interfaces that make credential ownership and component boundaries clear.
- **U2-NFR-28**: Document prerequisites, provisioning order, safe rerun behavior, explicit rotation/reset procedures, failure recovery, and the post-ETL reader-grant step.
- **U2-NFR-29**: Operators use an explicit command or one-shot Compose action with readable per-component results. No persistent identity-management service or custom administration UI is required.
- **U2-NFR-30**: Provisioning output includes the next required operator action when a permission or identity is deferred to a later unit.

## Explicitly Excluded NFR Targets

- Production identity federation, enterprise secret management, HA, and disaster recovery.
- Bulk user provisioning, concurrent orchestration, and multi-host operation.
- Automatic credential rotation or automatic destructive rollback.
- Performance benchmarking or provisioning-time SLA.
- Monitoring/alerting infrastructure or a custom administration UI.
- Relaxing credential separation or writer least privilege to bypass a component limitation.
