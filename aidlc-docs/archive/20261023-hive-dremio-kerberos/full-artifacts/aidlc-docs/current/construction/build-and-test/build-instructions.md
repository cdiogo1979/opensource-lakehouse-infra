# Build Instructions — Unit 1 Foundation

## Prerequisites

- Docker Engine/Desktop with Docker Compose v2 and BuildKit.
- Python 3 and OpenSSL on the host for local credential/config generation.
- Network access to the configured container registries and Maven Central during first build.
- On arm64 hosts, Docker amd64 emulation for the pinned Hive 3.1.3 image.
- Sufficient Docker memory for Dremio, Spark, RustFS, Hive, PostgreSQL and the KDC. No hard resource target is part of the approved PoC requirements.

The stack uses digest-pinned upstream images where applicable. Hive is built locally from the digest-pinned Apache Hive 3.1.3 base and adds PostgreSQL JDBC 42.7.14 plus the Hadoop 3.1.0-matched S3A connector and AWS SDK bundle. The Boto3 initializer image installs the exact dependency in `infra/bucket-init/requirements.txt`. Hadoop Kerberos settings are rendered into both `core-site.xml` and `hive-site.xml`; the Metastore uses the `hive/_HOST@REALM` service principal.

## Environment and credentials

The root `.env` file contains non-secret Compose settings. Run `scripts/bootstrap-local.sh` before invoking Compose directly. It creates ignored `.runtime/credentials/` files and renders the local Hive configuration without printing values. Do not delete or regenerate credentials while existing volumes are in use.

## Build and configuration checks

```bash
./scripts/bootstrap-local.sh
docker compose config --quiet
docker compose build kdc create-bucket hive-schema-init hive-metastore
docker compose pull --ignore-buildable
```

Expected result: Compose configuration parses successfully; local KDC, bucket initializer, and Hive images build; external digest-pinned images are available locally. The Hive image build downloads the pinned JDBC artifact from Maven Central.

To build and start the full default foundation with ordered readiness checks:

```bash
./scripts/start.sh
```

The successful Unit 1 runtime check includes a Kerberos-authenticated Spark `SHOW NAMESPACES` and temporary namespace create/drop against Hive Metastore. It does not create sample databases/tables; later units must create those as `write-service-account` and verify authorization. The optional `workload` profile contains the existing TPC-H data generator; its legacy generator image is outside the default foundation build and is not used by the Hive catalog tests.

## Verify the build outputs

```bash
docker compose images
docker compose ps --all
```

Build artifacts are local Docker images. No binaries or generated credentials are written to tracked source paths.

## Troubleshooting

- **Registry or Maven download failure**: check Docker/host network access, then rerun the build command.
- **Hive image fails on arm64**: confirm Docker Desktop amd64 emulation is enabled; this is expected for the accepted Hive 3.1.3 baseline. Hive startup can take substantially longer under emulation; check `docker compose ps --all` and `docker compose logs hive-metastore`. If Kerberos SASL initialization fails, verify `hadoop.security.authentication=kerberos` is present in rendered `core-site.xml` and the service keytab principal matches the configured `_HOST` principal.
- **Compose reports missing `.runtime` files**: run `scripts/bootstrap-local.sh`; it preserves existing credential files.
- **PostgreSQL schema initialization fails**: inspect `docker compose logs hive-schema-init metastore-db`. The initializer does not drop or upgrade an existing schema.
- **KDC reports a stale keytab/database mismatch**: use `scripts/clean.sh` only if a full local data reset is intended; it requires the exact confirmation phrase.
