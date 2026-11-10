# Unit 3 Infrastructure Design Plan — RustFS Buckets and Polaris Credential Vending

## Objective

Create the three approved RustFS buckets without deleting existing data, provide the protected server-side credential Polaris needs to call RustFS STS, and verify short-lived credentials are restricted to the intended bucket/prefix. Human and Spark clients continue to use Polaris; they do not receive static RustFS keys.

## Approved interfaces

| Environment | Polaris catalog | Namespace | RustFS location |
|---|---|---|---|
| Production | `lakehouse` | `default_lh` | `s3://bucket-default/default_lh/` |
| Dev | `lakehouse-dev` | `default_lhdev` | `s3://bucket-default-dev/default_lhdev/` |
| UAT | `lakehouse-uat` | `default_lhuat` | `s3://bucket-default-uat/default_lhuat/` |

Groups map to Polaris principal roles. Polaris catalog authorization determines which environment locations are available; Polaris requests RustFS STS credentials with a session policy scoped to the authorized Iceberg location and operation. RustFS root credentials remain protected operator/runtime inputs and are not returned to clients. The RustFS 1.0.4 STS API clamps session lifetimes to a minimum of 900 seconds; this limit must be recorded and checked against the approved “short-lived” requirement.

## Design decisions

- Use the pinned RustFS 1.0.4 S3-compatible endpoint and path-style access.
- Configure internal RustFS service address for Polaris and loopback S3 endpoint for the local host-side verifier.
- Keep the RustFS root access/secret keys in `.runtime/credentials`; inject them only into the generated Polaris application properties, which are protected and mounted read-only. The Spark/client configuration must never contain these bootstrap credentials.
- Create buckets with an idempotent host-side Python standard-library helper using SigV4; do not add an always-running bucket-init service or a new package dependency.
- Never empty, delete, or recreate an existing bucket. Verify existing buckets and preserve their contents.
- Validate STS session restrictions with one unique temporary object under a dev probe prefix and remove only that exact test object using the same temporary credentials.
- Do not configure RustFS Console OIDC for this journey. That integration is a Console SSO flow, not the Polaris/Spark credential-vending mechanism.
- Catalog definitions and their storage configuration remain created by U4's product bootstrap CLI; U3 validates the storage/STS contract and provides the operator steps/config inputs.

## Verification plan

- Validate code compilation, file permissions, Compose configuration, and bucket naming.
- Ensure all three approved buckets exist idempotently.
- Request RustFS `AssumeRole` with an inline policy for a unique dev prefix; verify dev listing/object operations succeed and production bucket operations fail.
- Verify the exact probe object is removed and no other objects are changed.
- Confirm no STS access key, secret key, session token, RustFS root key, or Polaris bootstrap credential appears in output.
- Confirm Polaris runtime config contains the protected S3 backend credentials and the Spark/client path does not.
- Record the 15-minute RustFS STS minimum and any remaining Polaris 1.8.0 interoperability limits.

## Status

**Approved direction derived from the parent intent and approved Application Design.** Implementation and live checks are in progress. Do not close U3 until Polaris itself successfully vends credentials through its Iceberg REST API and a Polaris-aware Spark client completes the allowed/denied storage checks; those integrated checks belong to U4.
