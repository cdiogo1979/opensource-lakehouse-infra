# Domain Entities — Unit 1 Identity Provisioning

## StarRocks Service Identity

**Meaning:** The logical non-human platform identity under which StarRocks accesses external catalog and object storage services.

**Attributes:**

- Logical owner: `starrocks`
- Provisioning result: aggregate lifecycle/status for provider identities
- Credential references: separate Kerberos and RustFS references

**Relationships:** Owns exactly one Kerberos identity reference and one RustFS identity reference. It is not a StarRocks SQL login; SQL users are managed by Unit 3.

## Kerberos Identity

**Meaning:** The KDC principal used by the StarRocks service to authenticate to Hive Metastore.

**Attributes:**

- Principal: `starrocks@<realm>`
- Keytab reference: `.runtime/credentials/keytabs/starrocks.keytab`
- Validation state: present, TGT-validated, failed, or not attempted

**Invariants:** No end-user keytab is reused. Existing principal keys are not changed during provisioning. A TGT must be obtainable before the identity is reported ready.

## RustFS Identity

**Meaning:** The S3-compatible account used by StarRocks to read/write Iceberg objects.

**Attributes:**

- Access-key ID: `starrocks`
- Secret reference: `.runtime/credentials/rustfs-starrocks-secret-key`
- Bucket: `lake`
- Policy reference: `lakehouse-starrocks`
- Validation state: account/policy present, scoped authentication validated, failed, or not attempted

**Invariants:** Secret material is independent from Kerberos and all existing platform credentials. Existing secrets are never silently replaced. The policy allows only the current databaseA and databaseB warehouse prefixes.

## Storage Policy

**Meaning:** The named RustFS permission set attached to the StarRocks RustFS Identity.

**Attributes:**

- Name: `lakehouse-starrocks`
- Allowed object scopes: `lake/warehouse/databaseA.db/`, `lake/warehouse/databaseB.db/`
- Allowed operations: read/write actions required by the later-approved Iceberg integration, limited to those scopes
- Validation state: absent, compliant, drifted, or created

**Invariants:** An absent policy may be created. An existing policy with broader or mismatched access is not overwritten; provisioning fails and preserves it for operator reconciliation.

## Credential Reference

**Meaning:** A non-secret locator for protected local credential material consumed by a provider or service.

**Attributes:**

- Provider: Kerberos or RustFS
- Local reference path
- File availability and protected-permission status
- Secret value is never stored in workflow status or emitted to logs

**Invariants:** The reference can be reported, but credential contents cannot. Existing files are preserved by local bootstrap; missing files are created with protected permissions according to the project convention.

## Provisioning Result

**Meaning:** Redacted status for one provider or the aggregate StarRocks identity provisioning operation.

**Attributes:**

- Provider name
- Outcome: created, already-present, validated, failed, or not-attempted
- Safe diagnostic class/code
- Aggregate state: ready, partially provisioned, retryable failure, or reconciliation required

**Invariants:** A partial failure does not delete successful provider resources. Retry is safe and idempotent. Existing credential or policy drift is distinguished from retryable service failures. Secret material, keytab contents, signed headers, and raw credential-bearing responses are excluded.
