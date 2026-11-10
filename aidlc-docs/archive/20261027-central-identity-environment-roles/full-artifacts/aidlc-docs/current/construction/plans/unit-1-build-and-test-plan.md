# Unit 1 Build and Test Plan — FreeIPA Identity Foundation

## Objective

Validate the drafted isolated FreeIPA profile, bootstrap identities, scoped role-membership workflow, service keytabs, and protected state interfaces before any downstream service is attached. The running MIT KDC remains the only active authority throughout this plan.

## Preconditions and safety boundary

- The approved Code Generation artifacts are present; local bootstrap credentials were generated with `scripts/bootstrap-local.sh` and are ignored/protected.
- Confirm that the configured validation subnet does not overlap host, VPN, or existing Docker ranges.
- Use only the `freeipa-validation` Compose profile and its dedicated network. Do not publish LDAP/Kerberos/DNS ports or attach production clients.
- Do not change MIT KDC state, active `krb5.conf`, current keytabs, RustFS credentials/buckets/objects, Hive configuration, or administrator component mapping.
- Do not run cutover, rollback, or any command that deletes/recreates persistent data.
- Keep the test identity bootstrap in `/data` of the current isolated volume `iceberg-poc-freeipa-validation-data-nss-patched2`; human accounts have no passwords yet and must not be considered ready for JupyterHub authentication.

## Build and Test sequence

### 1. Static configuration checks

- Check Compose rendering, FreeIPA image reference/digest, ports, mounts, secrets, networks, and profile selection.
- Check shell syntax and permissions for the new FreeIPA helpers; verify `.runtime` is ignored and bootstrap files are owner-only without printing values.
- Confirm the default Compose stack still references the existing MIT KDC and its current keytabs.

### 2. Isolated FreeIPA startup

- Start only `freeipa-validation` and wait for the LDAP TLS plus Kerberos readiness check.
- Confirm the image starts on the target ARM64 Docker Desktop host and persistent `/data` initializes successfully.
- Verify only loopback HTTPS is published; LDAP, Kerberos, DNS, and password-change ports remain internal.
- Validate the FreeIPA certificate chain and hostname, LDAP GSSAPI query, KDC ticket acquisition, FreeIPA DNS SRV/FQDN resolution, and Docker embedded-resolver forwarding.

### 3. Identity and least-privilege checks

- Run the one-time bootstrap and verify the built-in `admin`, approved users, three groups, and intended base membership.
- Verify service keytabs contain their expected isolated principals and authenticate: Hive FQDN-qualified principal, writer user principal, StarRocks user principal, and scoped membership-manager service principal.
- As the scoped principal, add and remove a test user from each approved role group and verify the final membership state.
- Prove the scoped principal cannot edit an unrelated group, create/delete users or services, change passwords, or retrieve arbitrary keytabs. Test with a disposable non-production group/object and remove only test objects after recording the result.
- Confirm rerunning bootstrap does not replace existing generated keytabs or alter an existing account/password.

### 4. Persistence and backup rehearsal

- Stop and recreate the isolated FreeIPA container without removing the current isolated volume; verify identities, groups, role permissions, and service keytabs persist, if initialization reaches readiness.
- Create and inspect a stopped-service backup of the FreeIPA named volume's `/data` and confirm the MIT rollback inventory is readable without exposing keytab/password contents.
- Rehearse restore in a separate isolated copy only. Do not restore over the active validation data or MIT volume.

### 5. Preservation and cleanup

- Verify the active MIT KDC remains healthy and its database/keytab/client configuration are unchanged.
- Verify RustFS writer S3 key identifier, production `lake` bucket/object references, and existing admin privilege mapping are unchanged.
- Stop the validation container while retaining its state for review. Do not remove volumes or credentials.
- Capture sanitized command results, image digest, timing, and pass/fail evidence. Record any FreeIPA CLI or Docker Desktop incompatibility as a failed gate; do not work around it by switching architectures without design review.

## Acceptance criteria

- Isolated FreeIPA readiness, TLS, Kerberos, DNS, and persistence checks pass.
- Approved identities/groups and validation keytabs exist; the scoped identity can only inspect/change membership in the approved groups.
- Unrelated group/identity/keytab operations are denied.
- Protected file modes and secret/log handling meet the approved NFRs.
- Backup and isolated restore rehearsal are readable and do not alter the live MIT KDC or production data.
- Preservation checks confirm the MIT authority and existing RustFS/admin state remain unchanged.

Any failed acceptance criterion blocks Unit 1 completion and authority cutover. Hive FQDN principal migration and integrated consumer testing remain in Unit 6; JupyterHub passwords/session behavior, RustFS policies, Hive authorization, and Ranger/StarRocks behavior remain in their assigned dependent units.

### Approved AlmaLinux 9 image retry — 2026-10-27

The user approved testing the upstream FreeIPA 4.13.1 AlmaLinux 9 image after the AlmaLinux 10 image failed during Dogtag CA-agent PKCS#12 import. Pulled `docker.io/freeipa/freeipa-server:almalinux-9-4.13.1` for `linux/arm64`, resolved digest `sha256:55c52a1cd24b80e7e9ddc480f00704c4cc5fd311a56720917b9961d6821ff23c`, and updated Compose and design artifacts. The run uses a fresh named volume `iceberg-poc-freeipa-validation-data-alma9`; all earlier partial volumes and the active MIT KDC remain untouched.

**Result**: Failed. The AlmaLinux 9 run reproduced the same failure during Dogtag setup. Filtered `ipaserver-install.log` evidence shows Dogtag started its CA subsystem successfully, but FreeIPA then failed importing `/root/ca-agent.p12` into a temporary NSS database: `pk12util` returned 19 with `SEC_ERROR_PKCS12_UNABLE_TO_IMPORT_KEY` (“Error attempting to import private key”), wrapped as `Pkcs12ImportUnknownError` at step 19/32 while requesting the RA certificate. The container exited with status 123 and became unhealthy before FreeIPA readiness. This narrows the failure to importing the private key from the generated CA-agent PKCS#12; the available logs do not identify why NSS rejects that key. The new partial volume and all earlier partial volumes remain intact. The active MIT KDC remains `running/healthy`; no cutover or downstream attachment occurred. Validation-only installer passwords were replaced in protected files after the local option file was inadvertently included in diagnostic output; the replacements apply to future initialization and do not rewrite the failed volume's contents. Temporary diagnostic log copies were removed.

### PKCS#12 failure investigation — 2026-10-27

- Both the AlmaLinux 9 and AlmaLinux 10 image variants use FreeIPA 4.13.1 and NSS `3.124.0-5` on ARM64. The unmounted images report crypto policy `DEFAULT`; `/proc/sys/crypto/fips_enabled` is absent, so there is no evidence this run is in kernel FIPS mode. Changing only the OS variant therefore did not address the issue.
- In an unmounted throwaway AlmaLinux 9 container, a generated RSA-2048 certificate/key exported and imported through NSS `pk12util` successfully. This rules out a basic RSA PKCS#12 round-trip failure in that simple path, but it does not exercise Dogtag's CA-agent export or FreeIPA's temporary database.
- The failing install log records Dogtag's own `pki pkcs12-export` completing before FreeIPA's `pk12util` fails at private-key import. The available sanitized evidence cannot determine whether the failing input is specific to Dogtag's PKCS#12 encoding, generated key attributes, password handling, or FreeIPA's import database/context. Do not infer a root cause from the generic NSS error.
- A stopped-container diagnostic confirmed `/root/ca-agent.p12` remains in the validation container's writable layer, but the Dogtag directory has no retained password file and `/var/log/ipaserver-install.log` is empty in the stopped container. Listing filenames and checking log size did not expose credentials. The PKCS#12 file was not copied to the host or printed.
- The exact-file NSS import could not be run because the PKCS#12 passphrase was not retained after installer failure. A fresh unmounted image cannot reproduce Dogtag's export because the CA trust/configuration has not been initialized there. No helper container, new install, image/configuration change, or volume reset was performed.
- The user approved instrumented first-install diagnostics on fresh isolated named volumes. The first run reproduced the error but its result markers were captured by systemd; a second wrapper revision persisted only sanitized codes and identifiers to the dedicated validation volume. All private key and password copies stayed on container tmpfs and were discarded with each container. No active KDC or workload component was attached.
- On the second instrumented import, `pk12util` returned 19 for the original target NSS database, a fresh NSS database, and a copy of the target NSS database. This rules out the target database state as the sole cause.
- OpenSSL 3 parsed the captured CA-agent PKCS#12 metadata and verified its SHA-256 MAC using the same passphrase supplied to NSS. The encrypted key bag uses PBES2/PBKDF2 with AES-256-CBC and HMAC-SHA256. OpenSSL could not extract/decrypt the private-key bag using that passphrase; a legacy-PBE re-export therefore could not be attempted. NSS likewise returned 19 for a fresh and cloned database. This localizes the failure to the PKCS#12 key bag/decryption or its password/encoding, rather than the outer integrity MAC or target NSS database. The exact reason remains unresolved; do not assume an algorithm compatibility fix without further evidence.
- Five instrumented attempts used separate named volumes: `iceberg-poc-freeipa-validation-data-instrumented` through `...-instrumented5`. Preserve these, along with the original four partial volumes. The current container exits with status 123 before readiness. No identity cutover or active MIT KDC change occurred.
- The private-key-safe investigation has narrowed but not resolved the failure. Build and Test remains blocked. The next decision is whether to approve deeper FreeIPA/Dogtag exporter investigation or reconsider the identity architecture. Do not change the active identity authority or modify MIT KDC state during that review.

## Approval Gate

The user approved this plan on 2026-10-27 and requested continuation. Build and Test began on 2026-10-27.

## Execution Results — 2026-10-27

### Passed

- `docker compose --profile freeipa-validation config -q` rendered successfully with temporary, non-secret values for unrelated Airflow-required variables.
- `bash -n` passed for the bootstrap, FreeIPA validation, CA export, identity-provisioning, readiness, identity-bootstrap, and role-membership scripts.
- `scripts/bootstrap-local.sh` generated the protected FreeIPA local bootstrap files without displaying values. Its first run exposed a missing-`.env`-key fallback bug; the run succeeded with `.env.example` defaults supplied in the environment. `scripts/bootstrap-local.sh` was corrected to use its default when a key is absent from an existing `.env`.
- `.runtime` and `.runtime/credentials` are mode 0700; generated FreeIPA password/options files are mode 0600. `.runtime/` is covered by `.gitignore`. The failed legacy `.runtime/freeipa/data` directory is mode 0700 and retained for diagnosis; it is no longer mounted by Compose.
- The configured `172.30.250.0/24` subnet did not overlap other Docker networks. The preflight initially failed because one existing network returned `IPAM.Config: null`; `infra/freeipa/check-network.py` now handles that valid Docker response and the rerun passed. Host/VPN route overlap was not independently verified.
- The pinned image pulled as `linux/arm64`, digest `sha256:77630c5325f2a506f68ff8e2caed008632075d5e7518583f9799897a527a42b9`.

### Failed gate

- The first FreeIPA container initialization exited with status 2 while populating the image's `/tmp`/`/data` templates. Logs contain repeated `tar: etc/...: Cannot open` and symlink-creation `Permission denied` errors. This is a startup failure on the current Rancher Desktop host; the container did not reach the FreeIPA readiness check.
- A throwaway run of the same template helper succeeded with the image's anonymous `/tmp` volume but reproduced the permission errors when writing the template into a fresh host bind mount under `/private/tmp`. This isolates the failure to host bind-mount behavior on the current runtime. The temporary diagnostic directory was removed; `.runtime/freeipa/data` was retained.
- The user approved revising Infrastructure Design to use a named Docker volume for FreeIPA `/data`. The initial attempt used `iceberg-poc-freeipa-validation-data` and exited before readiness; that partial volume and the earlier bind-mount data remain untouched.
- The installer log identified `Unable to determine the amount of available RAM`. With the image's required host cgroup setup, memory controller files are exposed under a nested `/sys/fs/cgroup/docker/...` path, but FreeIPA checks the root. Docker's default private cgroup namespace exposed root-level memory files in a temporary container but caused the systemd-based FreeIPA container to exit before setup could resume. The pinned image source confirms support for `--skip-mem-check`; available memory independently reported 7.2 GB in a temporary container. Compose retains the image's host cgroup setup, and bootstrap options now use that supported installer flag. The prior partial named volume `iceberg-poc-freeipa-validation-data` and failed private-cgroup attempt volume `iceberg-poc-freeipa-validation-data-retry1` remain untouched; Compose targets `iceberg-poc-freeipa-validation-data-retry2`.
- The next installer attempt failed validating `127.0.0.11` as a DNS forwarder: Docker DNS returns an empty response to a root SOA query. Read-only probes confirmed public DNS resolvers answer the check and showed `7.2 GB` available RAM at the time. Bootstrap now supports `FREEIPA_DNS_FORWARDER` (default `1.1.1.1`) and updates only the forwarder option without printing other installer options. FreeIPA DNS forwarding for Compose service names remains an integration gate; it is not considered passed by this bootstrap resolver change.
- With the external DNS forwarder, first-install progressed through Directory Server, Kerberos KDC, and into Dogtag CA setup, then exited with status 123. FreeIPA reports `Pkcs12ImportUnknownError` while importing its generated `/root/ca-agent.p12`; the PKI spawn log does not reveal a clear cause. Build and Test is blocked pending review of the pinned image/CA setup. All three partial volumes are retained. A diagnostic process listing included the two newly generated validation-only installer passwords; they were replaced in protected credential files and the options secret, all mode 0600. No active MIT or RustFS credentials were changed.
- Only the isolated `freeipa-validation` service was started. The active MIT KDC, active `krb5.conf`, existing client/service keytabs, RustFS identities/buckets/data, Hive, and administrator mapping were not targeted.
- The existing `iceberg-poc-kdc` container is running and healthy. No before/after comparison of its database, keytabs, or client configuration was performed.
- The FreeIPA state directory now contains partially populated image-template files. It has been retained; no data or Docker volumes were deleted. The failed container is exited.

### Not run

Identity/group and keytab bootstrap, TLS/Kerberos/DNS readiness, scoped-role positive/negative authorization, persistence/restart, backup/restore, and preservation verification are not verified because the server failed before readiness. Unit 1 Build and Test remains open and the failed startup is a blocking gate; do not proceed to authority cutover.

## Resolution — 2026-10-27

FreeIPA startup was fixed and verified in isolation. Reproduced the native `pk12util` private-key import failure on FreeIPA 4.13.4, then confirmed Dogtag's JSS importer successfully imports the same PKCS#12. Patched the container image so the temporary FreeIPA CertDB falls back to Dogtag's JSS importer if `pk12util` fails. Patched RA issuance to submit the generated CSR through Dogtag's CLI using NSS client-certificate authentication, approve the request if Dogtag returns `pending`, and export the completed certificate. The private key remains inside the NSS database. The CLI connects using the FreeIPA server hostname and trusted CA; revocation checking is skipped during this local first-install bootstrap because its OCSP endpoint is not ready.

The image build succeeded. A new normal `freeipa-validation` installation completed successfully using named volume `iceberg-poc-freeipa-validation-data-nss-patched2`; `scripts/freeipa-validation.sh start` returned success after the configured healthcheck passed. The healthcheck uses the host keytab to obtain a Kerberos ticket and performs an LDAP-over-TLS query. Rebuilding/recreating the container on the same named volume also passed readiness. The prior partial volumes, including `iceberg-poc-freeipa-validation-data-nss-patched`, remain untouched. The active MIT KDC was not changed.

The isolated Unit 1 validation gates are complete with the results below. Downstream JupyterHub/Hive/RustFS integration, Hive service-name DNS on the eventual shared network, and coordinated client migration remain assigned to their dependent units. FreeIPA remains isolated; do not perform authority cutover as part of this test completion.

### Isolated startup resolution and identity bootstrap — 2026-10-27

- The FreeIPA UI host-port patch was verified: `https://ipa.lakehouse.local:8443/ipa/ui/` returned HTTP 200, including after identity bootstrap recovery and container recreation.
- The first identity bootstrap created the three role groups and four approved identities, then stopped while registering the Hive service principal. `ipa service-add` attempted a DNS lookup for `hive-metastore.lakehouse.local`, which Docker DNS could not resolve. The bootstrap now uses FreeIPA's `--force` option for that explicitly registered host object; the Hive service principal was created and the idempotent bootstrap completed.
- That first bootstrap revision also reused FreeIPA's own `HTTP/ipa.lakehouse.local` server principal as the automation identity. `ipa-getkeytab` rotated its key, which caused the scoped API request to fail. The server's GSSProxy HTTP keytab was refreshed in the isolated FreeIPA instance and the GSSProxy/HTTP services restarted; the UI returned HTTP 200 afterward. The code now uses a distinct `lakehouse-membership/ipa.lakehouse.local` principal and removes the obsolete HTTP principal from the membership role. Do not export or use the stale `/data/lakehouse-provisioner.keytab` generated by the earlier revision.
- The corrected bootstrap completed and created the approved role groups, identities, FreeIPA services and protected keytabs. The approved base memberships were confirmed. Kerberos authentication succeeded for the Hive, writer, StarRocks, and dedicated membership keytabs.
- The scoped role-management helper successfully added and removed the existing `starrocks` identity in each of the three approved groups, restoring its original membership state. With a temporary unrelated group, direct membership editing by the scoped principal was denied; the temporary group was cleaned up.
- FreeIPA's DNS server answered authoritative `_kerberos._tcp` and `_ldap._tcp` SRV queries and resolved `ipa.lakehouse.local` to the validation server address. External DNS forwarding through the configured forwarder resolved a public A record. The isolated validation network does not contain Hive, so `hive-metastore.lakehouse.local` is not expected to resolve there; service-name resolution on the eventual shared client network remains a downstream integration check.
- The FreeIPA container was force-recreated with the same persistent volume `iceberg-poc-freeipa-validation-data-nss-patched2`. Readiness remained healthy, all four keytabs authenticated afterward, and the scoped membership add/remove check passed again. The pre-existing `iceberg-poc-kdc` remained healthy; no MIT KDC data or configuration was changed.
- The current host interface and route tables contain no subnet overlapping `172.30.250.0/24`; the Docker-network preflight also passed. `scutil --nwi` could not report network information, so overlap with a VPN profile that is inactive or not represented in the current route table remains environment-dependent.
- A password-scope test created a disposable user with the admin identity, then confirmed `lakehouse-membership` was denied when attempting to set that user's password. The disposable user was removed and its absence verified. Earlier checks also confirmed denials for unrelated group membership, user/service creation and deletion, and arbitrary keytab retrieval.
- A secret-safe scan found both installer passwords in the old backup's persistent system journal. Both FreeIPA passwords were rotated and verified after container recreation. The FreeIPA image now keeps journaling volatile. A runtime test wrote a marker to `/run/log/journal` and verified the persistent journal file did not change. The old credential-bearing backup was removed after replacement verification.
- A replacement backup was created from the stopped FreeIPA volume without `var/log/journal`, had mode 0600, passed archive integrity and current-credential scans, and was restored into a new isolated named volume. The restored state contained the expected FreeIPA database marker and service keytabs at mode 0600; no journal files were restored and the live validation volume was not overwritten.
- The final FreeIPA validation container and active MIT KDC both returned healthy. RustFS also remained healthy. The FreeIPA UI returned HTTP 200 after final recreation. Only loopback HTTPS is published; identity service ports remain internal.
- From a helper attached only to the validation network, Docker DNS resolved both `freeipa-validation` and `ipa.lakehouse.local` to the FreeIPA container. `hive-metastore.lakehouse.local` did not resolve on this isolated network, so cross-service DNS remains an integration gap; no client was attached to or configured against this validation profile.
- `bash -n` passed for the corrected bootstrap, membership, and validation scripts.

### Deferred to dependent units / environment-specific checks

- JupyterHub LDAP login and group restrictions, Hive and RustFS positive/negative authorization, DNS resolution of actual service names on a shared downstream network, and coordinated client migration remain assigned to dependent integration units.
- Host/VPN overlap was checked against the current interface and route state. VPN routes that appear only when a separate VPN is connected require a repeat of the preflight in that environment.
- A complete scan of all prior diagnostic artifacts outside the replacement backup remains unverified. The FreeIPA installer credentials have been rotated; current values are stored only in protected `.runtime/credentials` files.

Unit 1 isolated Build and Test is complete. These results do not authorize FreeIPA cutover or establish downstream JupyterHub, Hive, RustFS, or StarRocks integration; those remain separate gates. The existing MIT KDC remains the active authority.
