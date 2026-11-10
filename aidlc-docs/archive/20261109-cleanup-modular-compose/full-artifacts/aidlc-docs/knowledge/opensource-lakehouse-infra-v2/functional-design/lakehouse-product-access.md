# Functional Design — Lakehouse Product Access

Current functional design of the `default` data product's access model across Keycloak, Polaris, and RustFS. This file was relocated on 2026-10-30 from the retired `knowledge/hive-dremio-rustfs/functional-design/lakehouse-workload-and-access.md`, which is preserved in the [RustFS Keycloak OIDC intent archive](../../../archive/20261030-rustfs-keycloak-oidc/intent-summary.md). For architecture, see [`../application-design.md`](../application-design.md).

## Product roles

| Keycloak group / Polaris role | Production (`lakehouse`, `bucket-default`) | UAT (`lakehouse_uat`, `bucket-default-uat`) | Dev (`lakehouse_dev`, `bucket-default-dev`) |
|---|---|---|---|
| `role-default-owner` | manage | manage | manage |
| `role-default-developer` | read | read | read/write |
| `role-default-analyst` | read | — | — |
| `role-default-writer` (service role) | read/write | read/write | read/write |
| `role-platform-admin` | manage (as owner) | manage (as owner) | manage (as owner) |

- **Owner** manages the product's Polaris resources and data across environments.
- **Writer**: the service user `srv-default-writer` reads and writes all environments.
- **Platform admin**: `role-platform-admin` is owner-equivalent and has no Polaris role of its own.
  - Its Keycloak group carries the Polaris client role `role-default-owner`, and the reconciler gives its members the `role-default-owner` principal role.
  - RustFS has a policy named `role-platform-admin` that is identical to the owner policy.

## Platform admin in each service

| Service | `role-platform-admin` | `role-default-owner` |
|---|---|---|
| Polaris and RustFS | owner rights | owner rights |
| Airflow | `Admin` | `Admin` |
| Jenkins | `Overall/Administer` | `Overall/Administer` |
| JupyterHub | admitted, and Hub admin | not admitted |
| Keycloak | `realm-admin` of the `lakehouse` realm (`realm-management` client); no `master` access | none |
| StarRocks | `role_platform_admin` (manage) plus built-in `user_admin`, `db_admin`, `cluster_admin` | `role_default_owner` (manage) |

JupyterHub admits `role-default-developer`, `role-default-analyst`, and `role-platform-admin`. The Keycloak and JupyterHub rights were added at the user's request during the reset intent's Build and Test.

## Bootstrap identities (`infra/keycloak/bootstrap-users.json`)

| User | Group |
|---|---|
| `joe-developer` | `role-default-developer` |
| `peter-analyst` | `role-default-analyst` |
| `maria-owner` | `role-default-owner` |
| `srv-default-writer` | `role-default-writer` |
| `platform-admin` | `role-platform-admin` |

- **Password**: every user gets the documented local-development password `ChangeM3!`. It is permanent, with no required actions, and the email is `<user>@lakehouse.local`.
- **Create-only at start**: `infra/keycloak/bootstrap-realm.py` creates only missing users and never changes an existing user.
- **Enforce on demand**: `scripts/bootstrap-users.sh` (`infra/keycloak/bootstrap-users.py`) changes only the listed users. For each one it:
  - creates the user or updates the profile
  - resets the password, non-temporary
  - clears required actions
  - removes every other group
  - adds the default group

  It fails if the realm groups are missing. `scripts/bootstrap-default-product.sh` runs it after the realm bootstrap. Reconcile Polaris afterwards.
- **Writer credential**: `scripts/prepare-lakehouse-runtime.py` writes the writer's password file from the same JSON. A changed `srv-default-writer` password breaks Airflow and Spark writes until `bootstrap-users.sh` restores it.
- **Writer client**: `lakehouse-writer` is confidential, password grant only, with no browser flow and no service account. Tokens last 3600 s and carry the Polaris role mapper. It accepts any realm user's credentials, but tokens carry only that user's roles.

## Authorization layers
1. **Identity**: Keycloak groups supply identity and role claims.
2. **Catalog**: Polaris maps the approved role claims to Polaris principal roles and catalog grants. Polaris-mediated Iceberg access vends scoped, short-lived RustFS credentials. Workloads (Spark through Airflow or JupyterHub) never receive root or static RustFS credentials.
3. **Console**: RustFS console sessions carry the policies named by the user's `groups` claim. They govern direct object access in the console only.
4. **SQL engine**: StarRocks reaches Polaris as the writer-level service account `srv-starrocks`.
   - StarRocks roles, named after the groups, narrow each SQL user to the product matrix.
   - Polaris is the outer bound: nothing beyond writer, so no table drops through StarRocks, even for owners.
   - See `starrocks-sql-access.md`.

These layers are independent:
- Keycloak membership alone creates no Polaris grant; principals must be reconciled (`infra/polaris/reconcile-keycloak-groups.py`).
- Polaris grants do not grant RustFS console access.
- RustFS console policies do not grant catalog operations.
- StarRocks roles are granted from Keycloak groups by `infra/starrocks/reconcile-starrocks-users.py`, not by Polaris grants.

## RustFS console policies (`infra/rustfs/bootstrap-policies.py`)

**Policy shape**
- Each product group, and `role-platform-admin`, has a RustFS IAM policy of exactly the same name.
- Every policy allows `s3:ListAllMyBuckets` on `arn:aws:s3:::*`, which reveals bucket names only.
- Every other resource is one of the three bucket ARNs or their `/*` object ARNs.
- Statements are allow-only, and no policy contains an `admin:` action.

**Access levels**

| Level | Bucket actions | Object actions |
|---|---|---|
| read | `GetBucketLocation`, `ListBucket`, plus console metadata reads: `GetBucketPolicyStatus`, `GetBucketVersioning`, `GetBucketObjectLockConfiguration`, `GetBucketTagging`, `ListBucketVersions` | `GetObject`, `GetObjectTagging`, `GetObjectVersion`, `GetObjectRetention`, `GetObjectLegalHold` |
| read/write | read + `ListBucketMultipartUploads` | read + `PutObject`, `DeleteObject`, `AbortMultipartUpload`, `ListMultipartUploadParts` |
| manage | `s3:*` on the bucket and its objects | |

**Rules**
- A user in several groups receives the union of their policies; effective access per bucket is the highest level among the user's groups.
- A user with no group value naming an existing policy is refused a console session by RustFS. Other group values are ignored.
- **Bootstrap**:
  - creates missing policies
  - accepts canonically equal ones (order-insensitive comparison)
  - upgrades a policy only if it exactly equals its previous approved definition, the one without console metadata reads
  - refuses any other existing content without changing it, naming only the policy

## Failure behavior
- **Keycloak unavailable**: new token issuance, group reconciliation, and new RustFS OIDC logins fail. Already-issued tokens and console sessions remain usable until expiry. Root break-glass access to RustFS is unaffected.
- **Polaris principals**: Polaris needs a principal record for each Keycloak username before that user's data queries can be authorized. Reconcile after creating users or changing memberships.
- **Reconciler identity**: the reconciler and realm bootstrap currently use the protected local Keycloak bootstrap administrator. Replace it with a least-privilege identity before shared deployment.

## Verification
- **StarRocks (2026-11-09)**: the read and write matrix through StarRocks matched the Polaris matrix for all five bootstrap users. The Polaris read set gained `NAMESPACE_READ_PROPERTIES` so StarRocks can load namespace metadata.
- **Environment reset (2026-10-31)**:
  - a rebuild from nothing; five bootstrap logins with one group each and the right Polaris role
  - `bootstrap-users.sh` restored the defaults after password, group, and required-action changes, and left a user outside the list alone
  - platform-admin got 200 on the `lakehouse` admin API and 403 on `master`; owner got 403
  - JupyterHub login confirmed by the user
- **Spark journey (U4)**: the Spark smoke-table journey and positive/negative read/write behavior verified for developer, analyst, owner, and writer in all environments.
- **Token handling (U2)**: wrong-audience and expired-token rejection, and Keycloak-outage behavior, verified. That intent closed under a waiver for the human PKCE callback and some reconciliation failure paths.
- **RustFS console (2026-10-30)**:
  - property-based tests over the policy definitions
  - a headless login and authorization run with temporary users: analyst read-only on production and denied elsewhere; developer writes dev only; console metadata reads allowed in scope and denied out of scope; refusal without a product group
  - a user-confirmed interactive developer login through a bucket view
- **Known limitation**: the RustFS 1.0.4 console bucket-list page loops for non-admin users (rustfs/console#271). Use `/rustfs/console/browser?bucket=<name>`.
