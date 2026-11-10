# Unit 3 Storage Architecture — RustFS and Polaris STS

## Components and trust boundary

- RustFS 1.0.4 provides the S3-compatible API and AWS-compatible STS `AssumeRole` endpoint.
- The host-side storage bootstrap reads the protected RustFS root access/secret files and creates only absent approved buckets.
- Polaris receives the protected RustFS backend credentials through its generated, read-only application-properties mount. Polaris uses them server-side to sign STS `AssumeRole` requests and returns only temporary, policy-scoped credentials through the Iceberg REST credential-vending response.
- Keycloak OAuth identifies the human/writer at Polaris. Polaris catalog roles/grants authorize catalog operations; the generated STS inline policy and bucket location scope enforce the resulting S3 boundary. Ordinary users do not receive static RustFS credentials.
- RustFS Console OIDC is not part of this path. It authenticates Console sessions and does not replace Polaris-aware Iceberg access.

## Product storage map

| Environment | Catalog | Namespace | RustFS URI |
|---|---|---|---|
| Production | `lakehouse` | `default_lh` | `s3://bucket-default/default_lh/` |
| Dev | `lakehouse-dev` | `default_lhdev` | `s3://bucket-default-dev/default_lhdev/` |
| UAT | `lakehouse-uat` | `default_lhuat` | `s3://bucket-default-uat/default_lhuat/` |

Internal endpoint: `http://rustfs:9000`; local host endpoint: `http://127.0.0.1:9000`; path-style addressing; region: `us-east-1`.

## Credential lifetime

RustFS 1.0.4 STS clamps `DurationSeconds` to a minimum of 900 seconds. The test proved that an inline session policy restricts operations to a single requested dev object path and denies production bucket access. This is temporary scoped access, but the storage credential may remain valid for 15 minutes; the shorter five-minute Keycloak human token does not shorten an already-issued S3 credential. This limit is explicit in the build report and must be considered in the final access/revocation assessment.

## Lifecycle and safety

Bucket bootstrap performs HEAD before CREATE and preserves all pre-existing buckets and objects. STS verification generates a unique test object path, uses only its temporary session to delete that exact object, and does not use cleanup against any other object. Normal project stop/start preserves RustFS's named volume.

## Handoff

U4 creates Polaris catalogs with the matching `default-base-location`, `allowed-location`, RustFS internal/external endpoints, path-style setting, region, and STS endpoint. U4 must prove Polaris itself requests scoped STS credentials, Spark can create/read the smoke table in each catalog, cross-environment storage access is denied, and credential refresh works before the journey is marked complete.
