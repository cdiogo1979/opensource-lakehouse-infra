# Domain Entities — RustFS Role Policies and Reconciliation

## FreeIPA User

The canonical directory identity with a stable username and lifecycle state. The username is projected to a RustFS IAM user/access-key ID where an S3 credential is required. Passwords and Kerberos secrets are not copied into this entity or into RustFS policy state.

**Key attributes**: canonical username, enabled/disabled state, FreeIPA group memberships.

## Lakehouse Role Group

A canonical FreeIPA group used to assign a data role. Its RustFS group is a derived projection with matching canonical name and reconciled members.

**Supported roles**: `lakehouse-developers`, `lakehouse-analysts`, `lakehouse-writers`.

**Invariant**: A human user resolves to one supported data role in this design. Conflicting group membership blocks reconciliation. The non-interactive writer belongs only to the writer role; admin privilege is modeled separately.

## RustFS IAM User

A RustFS S3 identity keyed by the canonical username/access-key ID. It has enabled/disabled state and a key lifecycle managed separately from policy content. Its effective permissions are the merged result of its user policy attachments and all group policy attachments.

**Invariant**: Managed role users receive permissions from their role group only. Unexpected direct policy attachments are a drift conflict because RustFS merges policies.

## RustFS IAM Group

A RustFS group that projects one supported FreeIPA role group. Group membership is the reconciled set of RustFS users for canonical enabled FreeIPA members. The role policy is bound to this group.

## Role Policy

A named version-controlled IAM policy document that defines exact bucket and object actions/resources for one supported role. The policy is stored as a RustFS canned policy and its identity binding is attached to exactly one RustFS role group.

**Attributes**: stable policy name, policy version, role, ordered statements, canonical digest for local drift comparison.

## Bucket

An object namespace in RustFS.

| Bucket | Environment | Lifecycle owner |
|---|---|---|
| `lake` | Production | Existing platform; reconciler observes and preserves |
| `lake-dev` | Development | Reconciler ensures existence only |
| `lake-uat` | UAT | Reconciler ensures existence only |

**Invariant**: Bucket existence checks and create-if-absent preserve all bucket data. Reconciliation never deletes a bucket or migrates objects.

## RustFS Access Credential

An access-key identifier and secret used to sign S3 requests for an IAM user. Human credential delivery to notebook containers belongs to Unit 4. The writer's existing credential is a protected invariant for normal Unit 2 reconciliation. Root credentials are a separate administrative input and bypass IAM identity policies.

## Reconciliation Run

One invocation comparing observed FreeIPA/RustFS state to approved desired state.

**States**: `preflight`, `planned`, `applying`, `verifying`, `complete`, `no-change`, `blocked`, `partial-failure`.

**Attributes**: run identifier, start/end time, desired policy version, sanitized changes, verification outcomes, terminal state.

**Invariant**: A run is successful only if all managed state reads back exactly and role-based S3 probes pass. API success alone is insufficient; partial runs are visible and safely repeatable.

## Authorization Probe

A non-root S3 request issued with a role credential against a known bucket/key/action. Probe results record allowed/denied, bucket/environment, action category, and sanitized response class. Probe object keys are unique and disposable; cleanup targets only those created by the probe.
