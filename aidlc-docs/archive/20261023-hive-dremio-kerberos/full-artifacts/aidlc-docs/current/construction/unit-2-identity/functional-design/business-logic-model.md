# Unit 2 Identity and Permission Provisioning — Business Logic Model

## Purpose

Provide a repeatable setup coordinator that creates the approved Kerberos principals and component-native accounts, keeps their credentials distinct, and establishes the minimum initial permissions needed by later workload and query units. The provisioner coordinates component-owned interfaces; it does not decide authorization at query time.

## Actors

| Actor | Responsibility |
|---|---|
| PoC operator | Starts provisioning after Unit 1 services are ready, reviews redacted results, and requests explicit credential rotation or reset when needed. |
| Identity provisioner | Validates prerequisites, ensures principals/accounts/initial grants in order, records safe status, and stops on a required failure. |
| Kerberos KDC | Owns Kerberos principals and keytab issuance for `admin`, `write-service-account`, `user_a`, and `user_b`; retains the existing Hive Metastore service principal. |
| RustFS | Owns S3 access keys and policies for its administrator and writer identities. |
| Dremio | Owns local admin and writer accounts. It remains responsible for Space-level permissions and query identity mapping in the Dremio unit. |
| Metastore PostgreSQL | Owns its native database roles. Hive's metastore role remains service-only; writer credentials do not connect to this database. |
| Hive Metastore / Hadoop filesystem authorization | Owns Hive-side database/table access checks and effective identity behavior. The concrete authorization mechanism remains a feasibility gate. |
| Spark and JupyterHub | Consume identities and credentials. Spark has no separate account directory in this unit; JupyterHub's admin/user-session mapping is completed with Unit 5. |

## Identity and Credential Manifest

| Logical identity | Kerberos | Component-native credentials | Initial use |
|---|---|---|---|
| `admin` | Distinct principal and keytab | Separate admin credential/role for each component that does not use Kerberos; never reuse one component's native credential in another | Local administration and setup only |
| `write-service-account` | Distinct principal and keytab | Separate RustFS access key/policy and Dremio local account/password | Unit 3 sample ETL; requested Dremio JDBC object creation remains a later feasibility check |
| `user_a` | Distinct principal and keytab | Separate RustFS access credential/policy for its later Spark session; Dremio local query account created/configured by Dremio unit | Unit 4/5 read path; databaseA only |
| `user_b` | Distinct principal and keytab | Separate RustFS access credential/policy for its later Spark session; Dremio local query account created/configured by Dremio unit | Unit 4/5 read path; databaseA and databaseB |
| Hive Metastore service identity | Existing service principal and keytab are retained | None | Hive Thrift SASL endpoint |

Every identity's Kerberos, Dremio, RustFS, and PostgreSQL credentials are separate credential types. Native credentials for separate components are independently generated and stored; no credential value is reused across them. The writer and test-user credentials are distinct from admin credentials. User-specific Dremio, RustFS, and Jupyter session behavior is coordinated with the units that own those components.

## Provisioning Workflow

1. **Validate prerequisites.** Require healthy KDC, Hive Metastore, PostgreSQL, and RustFS; successful bucket initialization; Dremio's initial local setup complete before Dremio account operations; and writable, protected runtime credential storage. Do not print credential values during validation.
2. **Ensure Kerberos principals.** Create the four approved principals if absent. Preserve the existing Hive service principal and keytab. Create one keytab per principal; never export or copy a test user's keytab to another user.
3. **Ensure native component accounts.** Create separate Dremio, RustFS, and PostgreSQL administrator accounts/roles as supported. Create the writer's separate RustFS identity and Dremio local account. Record Spark's Kerberos identity contract; do not invent a Spark account store. Defer JupyterHub user/session setup to Unit 5.
4. **Apply initial permissions.** Assign only writer access needed for the approved warehouse prefixes and Hive create/populate operations. Do not grant writer access to PostgreSQL metastore credentials, component administrator roles, or Dremio platform administration. Set up separate user-specific RustFS credentials/policies for later read-path sessions, subject to the storage authorization feasibility check.
5. **Record status.** Report component and principal/account identifiers plus `created`, `already-present`, `deferred`, or `failed` status. Redact all passwords, access keys, secret keys, keytab content, and ticket material.
6. **Post-ETL reader-grant phase.** Once Unit 3 has created both databases, run a repeatable grant operation using the component-owned Hive authorization interface: `user_a` reads `databaseA`; `user_b` reads both. This phase is not an implicit side effect of initial identity setup and must not create sample databases or tables.
7. **Return truthful completion.** Mark provisioning complete only when every required identity and initial permission has succeeded or a specifically deferred unit-owned action is reported. An unsupported permission is a blocking result, not a success.

## Error and Recovery Flow

- A required prerequisite failure stops before mutation.
- A failure in a component adapter stops the current run, identifies the component and operation with a redacted diagnostic, and preserves all prior successful work.
- The operator may safely rerun the provisioner; each ensure action checks existing state and preserves credential material unless explicit rotation was requested.
- No automatic rollback deletes principals, accounts, keytabs, policies, buckets, database rows, or object data.
- Credential rotation is a separate operator action with explicit consumer update/restart ordering. It is not part of ordinary reruns.
- If a required component capability is absent, preserve the existing configuration and return evidence plus the smallest design adjustment for review.

## Authorization Boundaries

- Kerberos proves authentication to a service; it does not by itself grant database, object-store, Dremio, or PostgreSQL permissions.
- Hive Metastore and RustFS remain authorities for their respective checks. Provisioning creates identities and requested grants only.
- Spark consumes a caller identity; the Hive Metastore service identity does not replace the effective caller identity.
- Dremio local login and Space permissions are Dremio-owned. Unit 2 creates the required local admin/writer accounts, while source configuration, query-user mapping, and the non-admin Space write check remain with Unit 4.
- Admin access in components without Kerberos uses that component's separate native credential. Components without a user-account model (such as Spark's local runtime) receive an operator access procedure rather than a fictitious account.

## Observable Outcomes

Provisioning output identifies the principal/account, owning component, action status, and whether an operation is deferred to another unit. It records the effective identity only when the component exposes it. Any allow/deny demonstration reports the effective user and component decision without disclosing credentials.
