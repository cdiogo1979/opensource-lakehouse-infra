# Unit 1 Code Generation Plan — Spark Writer Runtime

## Unit Context

- **Unit**: Unit 1 — Spark Writer Runtime.
- **Story**: US-03 — Write lakehouse data as the configured writer.
- **Requirements**: FR-5; NFR-1; SWR-NFR-01 through SWR-NFR-06.
- **Dependencies**: Approved Unit 1 Functional Design, NFR Requirements, NFR Design, and Infrastructure Design; existing KDC, Hive Metastore, RustFS, and pinned Spark 3.5.5 service.
- **Workspace root**: `/Users/carlosdiogo/code_repo/hive-dremio-rustfs` (brownfield).
- **Service boundary**: Existing `spark` Compose service, including its current notebook endpoint, master, worker, and history server.
- **Identity boundary**: Existing `write-service-account@LAKEHOUSE.LOCAL` and existing RustFS writer credentials; no credential rotation or new identity.
- **Database entities**: None. No metastore schema or catalog data migration is part of Unit 1.
- **Interface contract**: Internal Spark master endpoint `spark://spark:7077`; worker uses the service TGT for Hive and the mounted file-backed writer S3 credentials for RustFS.

This plan is the single source of truth for Unit 1 Code Generation. Implement only the steps below. Test files and test execution are excluded in this stage; verification is deferred to the approved Build and Test stage.

## Sequential Generation Steps

### Step 1 — Implement the Spark writer lifecycle supervisor

- [x] Modify existing `infra/spark/entrypoint.sh` in place.
- [x] Keep startup and lifecycle control in the existing Bash entrypoint; do not add a helper service or language runtime. The only approved image package is Debian `krb5-user`, installed in Step 2.
- [x] Create and protect the service runtime state/cache paths, configure the explicit writer principal, keytab path, private `KRB5CCNAME`, and private AWS shared-credentials file path.
- [x] Read RustFS writer key/secret files without printing values; create an owner-only AWS `[default]` credentials profile under the private runtime tmpfs and set `AWS_SHARED_CREDENTIALS_FILE` to its path. Do not place secret values in ordinary environment variables, Spark defaults, command-line arguments, or logs.
- [x] Acquire and validate the writer TGT before starting the Spark master, worker, history server, or notebook. Implement the approved serialized lifecycle, 15-minute renewal margin, at-most-one-minute retry schedule, two-minute pre-expiry drain guard, graceful worker decommission, and worker restart/re-registration after recovery.
- [x] Start the master advertising `spark`, register the worker against `spark://spark:7077`, and manage the notebook as a child process while retaining the existing roles.
- [x] Handle container termination signals and child process exit without leaking credentials or orphaning supervised processes. Never force-kill active tasks to implement credential admission control.

### Step 2 — Wire the lifecycle into Docker Compose

- [x] Modify `docker-compose.yml` in place for the existing `spark` service.
- [x] Create `infra/spark/Dockerfile` to derive the Spark image from the existing pinned upstream image digest and install only Debian `krb5-user` for `kinit` and `klist`.
- [x] Configure the existing `spark` service to build that local image while preserving the pinned upstream base digest and all current Spark version/resource/network boundaries.
- [x] Update `scripts/start.sh` to build the local Spark image and fail with a safe setup instruction if the required writer keytab is missing.
- [x] Add the writer principal and non-secret credential/cache path environment settings.
- [x] Add the read-only writer keytab bind mount and existing RustFS writer Compose secrets.
- [x] Add the private `/run/krb5` 16 MiB tmpfs at mode `0700`; preserve read-only keytab/config mounts and all existing data mounts/volumes.
- [x] Add the KDC healthy startup dependency while retaining healthy object-store, successful bucket initialization, and healthy Hive Metastore dependencies.
- [x] Configure the master advertised hostname as `spark`; preserve the current loopback-only host bindings for Spark master and notebook UI.
- [x] Add the approved health check: 15-second interval, 5-second timeout, 3 retries, 60-second start period. It must require lifecycle readiness, a valid TGT, and worker registration.
- [x] Do not change unrelated services, published ports, resource limits, profiles, network ownership, or persistent volume definitions.

### Step 3 — Harden Spark-visible diagnostics

- [x] Modify `infra/spark/spark-defaults.conf` in place only to configure Spark redaction for credential-bearing configuration names and values.
- [x] Keep writer access/secret values out of this file; leave static Iceberg S3 credential properties unset so the SDK can use the private shared credentials file.
- [x] Preserve the existing Hive catalog, Kerberos, RustFS endpoint, and Iceberg settings.

### Step 4 — Update operator documentation

- [x] Modify `README.md` in place with the writer lifecycle behavior, required existing credential file paths, private-cache/health semantics, and internal endpoint `spark://spark:7077`.
- [x] Document safe startup/health inspection and explain that Build and Test must verify graceful decommission behavior.
- [x] Do not include secret values or introduce any credential rotation instruction.

### Step 5 — Write the Unit 1 code summary

- [x] Create `aidlc-docs/current/construction/unit-1/code/code-summary.md` with the modified files, lifecycle behavior, US-03 traceability, and remaining Build and Test verification items.
- [x] Mark this plan's implementation steps complete as each is finished and update `aidlc-docs/current/aidlc-state.md`.
- [x] Confirm no duplicate/alternate source files were created. Do not add or run tests during Code Generation.

## AWS Credential Source Rationale

The pinned Iceberg `S3FileIO` is configured to use the AWS SDK default credential chain when static `s3.access-key-id` / `s3.secret-access-key` properties are absent. The SDK supports a custom shared credentials file via `AWS_SHARED_CREDENTIALS_FILE`; therefore the entrypoint creates a private profile file from the existing mounted secrets and passes only the file path in the environment. This keeps secret values out of ordinary environment variables and Spark configuration. Confirm this provider path during Build and Test against the pinned Iceberg/AWS SDK versions. [AWS SDK for Java 2.x credential chain](https://docs.aws.amazon.com/sdk-for-java/latest/developer-guide/credentials-chain.html), [AWS SDK shared credentials file](https://docs.aws.amazon.com/sdk-for-java/latest/developer-guide/credentials-profiles.html), [Apache Iceberg S3FileIO properties](https://iceberg.apache.org/javadoc/1.8.1/org/apache/iceberg/aws/s3/S3FileIOProperties.html)

## Approval Gate

Review this complete plan. Explicit approval is required before any application code, Docker Compose, Spark configuration, or README changes are generated.

**Status**: Approved by the user on 2026-10-26 (`appprove and continue`), then revised with user approval on 2026-10-26 to build a local image from the same pinned Spark base digest with Debian `krb5-user` installed. Implementation may proceed within this revised scope. The image build and all runtime behavior remain for Build and Test; no tests are added or run during Code Generation.
