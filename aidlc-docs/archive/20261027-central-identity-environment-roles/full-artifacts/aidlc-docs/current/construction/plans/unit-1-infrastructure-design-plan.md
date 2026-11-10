# Unit 1 Infrastructure Design Plan — FreeIPA Identity Foundation

## Unit and Approved Baseline

Unit 1 adds FreeIPA to this local Docker Compose PoC and replaces the standalone MIT KDC in `LAKEHOUSE.LOCAL` after isolated validation. Service Kerberos keytabs are reissued; the writer's RustFS S3 key, production objects, and admin privilege mapping are preserved. Only one KDC authority may serve the realm at a time after cutover. The old MIT KDC database and matching keytabs remain protected rollback material until acceptance.

The current stack has a Compose service named `kdc`, a static `krb5.conf` pointing at `kdc:88`, no dedicated DNS service, and local-only administration endpoints. The FreeIPA container project provides upstream images and stores persistent server state under `/data`; its documentation warns that containerized FreeIPA adds deployment complexity. See [FreeIPA container documentation](https://www.freeipa.org/page/Docker.html) and the [upstream container project](https://github.com/freeipa/freeipa-container).

The approved NFRs require pinned versions, validated LDAP TLS, persistent FreeIPA state, restricted host exposure, protected file-backed secrets, an operator-created pre-cutover backup, readiness reporting, and a reversible staged cutover. This plan resolves the concrete image, DNS, storage, secret, TLS, network, cutover, and readiness design before infrastructure artifacts are generated.

## Infrastructure Design Checklist

- [x] Inspect current Compose KDC service, static Kerberos configuration, credential paths, and client network boundary.
- [x] Review upstream FreeIPA container deployment and persistent-data guidance.
- [x] Select the FreeIPA container image source and pinning approach.
- [x] Select hostname, DNS, and existing `kdc` service-name compatibility approach.
- [x] Select persistent `/data` storage and pre-cutover backup handling.
- [x] Select bootstrap secret delivery and FreeIPA CA trust distribution.
- [x] Select host-published ports and internal client connectivity.
- [x] Select isolated validation and staged cutover/rollback topology.
- [x] Select readiness/health check and dependent-service startup behavior.
- [x] Generate infrastructure-design artifacts and present them for approval.

Answers 1, 2, and 4–8 remain A. Question 3 was revised from A to B after Build and Test reproduced upstream template-copy permission errors on two host bind mounts under Rancher Desktop. The user approved a named Docker volume for FreeIPA `/data` on 2026-10-27. The failed `.runtime/freeipa/data` state is retained and is no longer the active FreeIPA state path. The initial image was the version-specific upstream `almalinux-10-4.13.1` variant.

### Approved image adjustment — 2026-10-27

After the AlmaLinux 10 variant reached Dogtag CA setup but failed importing its generated CA-agent PKCS#12, the user approved trying the same FreeIPA 4.13.1 release on the upstream AlmaLinux 9 variant using a new named volume. The `almalinux-9-4.13.1` image was pulled for `linux/arm64`; its resolved digest is `sha256:55c52a1cd24b80e7e9ddc480f00704c4cc5fd311a56720917b9961d6821ff23c`. Compose now targets `iceberg-poc-freeipa-validation-data-alma9`. All previous partial data volumes and active MIT KDC state remain untouched.

## Infrastructure Design Questions

Complete each `[Answer]:` field. The recommended options preserve the approved local Compose scope; choose `X` and describe the desired behavior if none fits.

### Question 1 — FreeIPA image source

Which image source should Unit 1 use?

A) Use the upstream FreeIPA container project image (`quay.io/freeipa/freeipa-server` or its Docker Hub mirror), select an OS-family tag compatible with the host/runtime, and pin an explicit image tag/digest after compatibility review. **(Recommended)**

B) Build and maintain a project-specific FreeIPA image from the upstream container recipes and pin its base/packages.

X) Other (describe the source and update ownership).

[Answer]:A

### Build and Test security correction — 2026-10-27

The upstream first-install wrapper passes the protected file-backed installer options to `ipa-server-install` as process arguments. A scan of the protected validation backup found the current administrator and Directory Manager passwords in persisted systemd journal metadata. Both credentials were rotated and verified. The FreeIPA image now configures systemd journaling as volatile and keeps `/run/log/journal` off the persistent `/data` volume, so installer process metadata is not retained in future backups. The original archive is retained with a compromised/do-not-restore label; a replacement backup excludes the historical journal. Fresh-volume runtime verification of the new journaling behavior is still required before treating the fix as verified.

### Question 2 — Hostname and DNS strategy

How should FreeIPA and clients resolve the server and realm services on the Compose network?

A) Use the FreeIPA integrated DNS and configure dependent containers to resolve the realm through it, while preserving Compose service discovery for other services. Infrastructure Design must specify the resolver integration and prove it works on the local Docker host. **(Recommended)**

B) Disable FreeIPA DNS and use explicit Compose hostname/network aliases plus configured Kerberos/LDAP server endpoints; document and maintain required service discovery records explicitly.

X) Other (describe the DNS/domain and client-resolution approach).

[Answer]:A

### Question 3 — Persistent state and backup source

Where should FreeIPA's `/data` and pre-cutover backups live?

A) Use an ignored project-local bind mount under `.runtime/freeipa/data` for persistent FreeIPA state. Before cutover, stop the relevant container and create a protected archive of the FreeIPA state plus the existing MIT KDC database, keytabs, and configuration; retain until acceptance.

B) Use a named Docker volume for `/data` and an explicit protected backup/restore procedure for the named volume and MIT rollback state. **(Approved 2026-10-27 after Build and Test showed bind-mount incompatibility on the current host.)**

X) Other (describe state location, backup method, and restore ownership).

[Answer]:B

### Question 4 — Bootstrap and provisioning credentials

How should installer, administrator, and service-provisioning credentials be supplied?

A) Use file-backed Compose secrets sourced from ignored `.runtime/credentials`; mount read-only, avoid passwords in Compose environment values/command arguments, and use a separate scoped service-principal provisioning identity after bootstrap. **(Recommended)**

B) Use a dedicated external secret manager or another protected mechanism; specify it in `X`.

X) Other (describe bootstrap storage, provisioning identity, and rotation ownership).

[Answer]:A

### Question 5 — TLS certificate authority

How should LDAP client trust be established?

A) Use the FreeIPA integrated CA for server certificates and distribute only its public trust certificate read-only to LDAP clients. Keep CA private material inside protected FreeIPA persistent state. **(Recommended)**

B) Use a separately managed local CA and provision a signed FreeIPA certificate/key; describe the certificate lifecycle and secret ownership in `X`.

X) Other (describe CA ownership and client trust distribution).

[Answer]:A

### Question 6 — Port publishing and network boundary

Which FreeIPA ports should be published on the host?

A) Keep all service-to-service LDAP/Kerberos/DNS traffic on the Compose network. Publish only the FreeIPA HTTPS administration interface to `127.0.0.1`; publish no LDAP, Kerberos, DNS, or password-change ports to external host interfaces. **(Recommended)**

B) Publish additional required ports to localhost for host-side client tests; list exact ports and use cases in `X`.

X) Other (describe host exposure and network restrictions).

[Answer]:A

### Question 7 — Validation and cutover topology

How should isolated validation transition to the active KDC?

A) Add FreeIPA as an isolated/explicit Compose profile with separate validation networking and persistent state. Once accepted, perform a documented maintenance cutover that disables MIT KDC authority, activates FreeIPA at the client-configured endpoint, installs replacement keytabs, and switches clients together. Preserve old KDC/keytabs for coordinated rollback. **(Recommended)**

B) Replace the existing `kdc` service definition directly and use a separate backup/restore branch for rollback; do not run both KDCs concurrently.

X) Other (describe the validation and authority-switch process).

[Answer]:A

### Question 8 — Readiness and startup dependencies

How should FreeIPA readiness gate identity provisioning and clients?

A) Add a dedicated readiness check that validates LDAP over TLS and obtains a Kerberos ticket for a required principal; mark the service healthy only after both succeed. Gate the identity provisioner and any service that requires FreeIPA on healthy status, with sanitized diagnostic categories. **(Recommended)**

B) Use only the FreeIPA container's process health and validate LDAP/Kerberos through an operator command before dependent services start.

X) Other (describe readiness probes and dependency behavior).

[Answer]:A

## Category Assessment

- **Deployment**: Local Docker Compose only; no cloud or production deployment target.
- **Compute**: One FreeIPA server container; no replica/HA node is required for the approved PoC.
- **Storage**: FreeIPA state is persistent; service credentials and rollback materials remain protected and distinct.
- **Networking**: Current clients share the internal Compose network and use static Kerberos settings; hostname/DNS strategy must be compatible with local Docker service discovery.
- **Security**: Validated LDAP TLS, least-privilege provisioning, restricted localhost publication, and secret-file mounts are mandatory.
- **Monitoring**: Use Compose readiness and operator-readable sanitized status; no monitoring stack is added.
- **Messaging**: Not applicable; Unit 1 adds no queue or broker.
- **Shared infrastructure**: Existing Hive, Spark, Airflow, StarRocks, RustFS, and data volumes remain in place; no bucket or production data changes.

## Approval Gate

After answers are resolved, check the topology against the current Compose network and approved NFRs. Generate `construction/unit-1/infrastructure-design/` artifacts and request explicit approval before Unit 1 Code Generation.
