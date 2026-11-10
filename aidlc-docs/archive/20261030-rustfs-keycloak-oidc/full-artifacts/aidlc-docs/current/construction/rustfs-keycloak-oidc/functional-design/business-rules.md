# Business Rules — rustfs-keycloak-oidc

## Admission and authorization
- **BR-1 Group-named policies**: RustFS maps each value of the ID-token `groups` claim to a RustFS policy of the same name (F1). The four product policies are the only RustFS policies whose names match product groups.
- **BR-2 Denial without a product group**: a user whose `groups` claim contains no name of an existing RustFS policy is refused a session by RustFS ("OIDC policy mapping did not resolve to current policies", F2). Other group values are ignored, never granted.
- **BR-3 Union**: a user in several product groups receives the union of their policies.
- **BR-4 Allow-only, bucket-scoped**: every policy statement is `Effect: Allow`, and every resource is one of the six environment-bucket ARNs or, only for `s3:ListAllMyBuckets`, `arn:aws:s3:::*`.
- **BR-5 Access matrix**: policies grant exactly the matrix in `domain-entities.md`, including the read-only console metadata actions of the `read` level. In particular, the analyst has no write action anywhere and no access to UAT or dev; the developer writes only to dev; no policy contains an `admin:*` action.
- **BR-6 Server administration stays root-only**: RustFS user, policy, and server configuration remain with the root break-glass identity (FR-3, FR-6).

## Keycloak client
- **BR-7 Exact URIs**: the `rustfs` client has exactly the two callback URIs and the two post-logout URIs for `localhost` and `127.0.0.1` on the configured console port; no wildcards; callbacks on the S3/API port are deliberately unregistered, so logins started there fail at Keycloak.
- **BR-8 Additive, fail-closed client bootstrap**: create the client and mapper when missing; accept identical existing configuration; refuse (no changes applied) on any conflicting client attribute, secret, URI, or mapper. Changing the console host port is a deliberate reconciliation that replaces only the known previous exact `rustfs` callback/logout values, following the Airflow precedent.
- **BR-9 Secret consistency**: the client secret in Keycloak must equal the protected file; a mismatch is refused, never overwritten silently.

## Policy bootstrap
- **BR-10 Idempotent policy provisioning**: for each of the four policies, create it when missing; when present, compare canonical forms and accept an identical policy; refuse a conflicting policy without changing it, and report which policy conflicts (no document content in errors).
- **BR-10a Exact-previous upgrade** (change 2026-10-30, clarification Q2: A): an existing policy that exactly equals the previous approved definition (before console metadata reads were added) is replaced by the current definition and re-read to verify; any other existing content is still refused.
- **BR-11 Order independence**: the bootstrap is safe to run before or after the Keycloak client exists and before or after RustFS OIDC is enabled.
- **BR-12 Root keys server-side only**: the bootstrap signs with the protected root keys read from `.runtime/credentials/`, never prints them, and never writes them elsewhere.

## Secret and configuration handling
- **BR-13 Secret creation**: `rustfs-oidc-client-secret` is created only if missing (0600, under a 0700 directory); its container mount copy is read-only.
- **BR-14 Secret delivery**: a wrapper reads the mounted file, refuses an empty or unreadable file, exports the value only for the RustFS process, and then runs the stock image entrypoint unchanged. The secret never appears in Compose files, `.env`, `docker inspect`, or output.
- **BR-15 Exact egress allowance**: `RUSTFS_OUTBOUND_ALLOW_ORIGINS` contains only `http://keycloak.localhost:8080`.
- **BR-16 Scoped name resolution**: the `keycloak.localhost` alias exists only on the internal RustFS identity network.

## Availability and break-glass
- **BR-17 Root break-glass**: root access-key login remains available and documented; enabling OIDC never removes or hides it.
- **BR-18 Keycloak outage**: new OIDC logins fail while Keycloak is unreachable; existing console sessions remain valid until their 3600 s expiry; root login keeps working. RustFS retries provider discovery in the background after startup failures.
- **BR-19 No regression**: Polaris STS vending, bucket bootstrap, and root-key S3 access behave exactly as before.

## Property identification (PBT-01; PBT Partial mode)
| ID | Property | Category | Enforced rule |
|---|---|---|---|
| P1 | `canonical(parse(serialize(policy))) == canonical(policy)` for generated policy documents | Round-trip | PBT-02 |
| P2 | Canonicalization is order-insensitive: shuffled actions/resources/statements yield the same canonical form | Invariant | PBT-03 |
| P3 | Every generated product policy satisfies BR-4 (allow-only, resources within the permitted ARNs) | Invariant | PBT-03 |
| P4 | For every combination of product groups, the effective access equals the per-bucket maximum of the members' matrix rows (BR-3, BR-5) | Invariant | PBT-03 |
| P5 | Conflict detection: an existing policy is accepted iff canonically equal to the desired one, upgraded iff canonically equal to the previous definition, and refused otherwise | Invariant | PBT-03 |

Generators (PBT-07) are domain-specific: product-group subsets, access levels, bucket names from the fixed set, and policy documents built from those; reusable across tests. Framework (PBT-09): Hypothesis, already pinned in `tests/requirements-pbt.txt`, with shrinking enabled and seeds printed on failure (PBT-08).
