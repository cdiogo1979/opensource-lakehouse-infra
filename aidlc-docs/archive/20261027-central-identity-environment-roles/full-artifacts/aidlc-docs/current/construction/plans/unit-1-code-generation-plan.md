# Unit 1 Code Generation Plan — Central Identity Foundation

## Unit Context

- **Unit:** Unit 1 — Central Identity Foundation.
- **Stories:** FreeIPA authority and group lifecycle foundations; detailed human authentication, object authorization, and downstream synchronization are completed by dependent units.
- **Requirements:** The approved identity, role, environment isolation, credential protection, and cutover requirements in `aidlc-docs/current/inception/requirements/requirements.md`.
- **Workspace:** `/Users/carlosdiogo/code_repo/opensource-lakehouse-infra` (brownfield Docker Compose platform).
- **Dependencies:** Existing MIT KDC, static Kerberos client configuration, Hive Metastore, RustFS, identity provisioner, and the approved Unit 1 Functional, NFR, and Infrastructure designs.
- **Completion boundary:** Add and validate FreeIPA in isolation, provision the agreed role groups, user identities, and service principals/keytabs, and prepare coordinated cutover/rollback artifacts. Do not make FreeIPA authoritative or change the running MIT KDC, client keytabs, RustFS credentials, buckets, or production data during code generation.

This plan is the single source of truth for Unit 1 Code Generation. Implement only these steps. Do not add or run tests during Code Generation; all runtime verification remains for Build and Test.

## Approved Contracts

- Kerberos realm remains `LAKEHOUSE.LOCAL`; following the approved image adjustment, Compose pins the upstream FreeIPA 4.13.1 AlmaLinux 9 variant and its verified ARM64 digest. The AlmaLinux 10 attempt and its Dogtag PKCS#12 failure remain in the build/test history.
- FreeIPA integrated DNS, LDAP/TLS, and Kerberos are isolated from the current MIT KDC for validation. The production Compose network and `kdc:88` compatibility endpoint are used only in a later coordinated cutover.
- FreeIPA state persists in the named Docker volume `iceberg-poc-freeipa-validation-data-retry1` mounted at `/data`. Bootstrap secrets are owner-protected files in ignored `.runtime/credentials` and are mounted read-only; do not put values in Compose literals, process arguments, logs, or committed configuration. The storage selection was revised after Build and Test reproduced host bind-mount permission errors on Rancher Desktop.
- Preserve the RustFS writer S3 access key/secret, `lake` production objects, existing admin privilege mapping, MIT KDC database, and current keytabs until the cutover is separately authorized and accepted.
- New identities are `developer-user`, `analyst-user`, `admin`, and `write-service-account`; role groups are `lakehouse-developers`, `lakehouse-analysts`, and `lakehouse-writers`. Do not remove `user_a` or `user_b` during Unit 1 code generation.
- FreeIPA provisioning uses a scoped service identity after bootstrap; it is separate from the platform `admin` identity. Consumer services receive only their own read-only keytab/trust material.
- No RustFS bucket/policy, Hive authorization, Ranger, StarRocks, Airflow, Jenkins, or JupyterHub login behavior changes in this unit unless needed strictly to define the FreeIPA service boundary. Those implementations belong to dependent units.

## Sequential Generation Steps

### Step 1 — Add isolated FreeIPA service and persistent state

- [x] Add an isolated FreeIPA validation service/profile and dedicated non-overlapping Compose network in `docker-compose.yml`; do not attach it to the active lakehouse network or assign the `kdc` alias.
- [x] Use the selected upstream version tag and pin the Docker Hub multi-platform index digest. Do not create an image build unless upstream runtime behavior proves it necessary and the issue is documented for review.
- [x] Mount the dedicated `iceberg-poc-freeipa-validation-data-retry1` named volume to `/data`; preserve `kerberos-kdc-data` and every existing volume untouched.
- [x] Provide installer inputs and bootstrap secrets using read-only file-backed Compose secrets. Ensure generated configuration and normal command output never contain secret values.
- [x] Publish only the FreeIPA administration HTTPS endpoint on loopback port `8443`; do not publish LDAP, Kerberos, DNS, or password-change ports.

### Step 2 — Implement validation DNS, trust, and readiness interfaces

- [x] Configure a stable FreeIPA FQDN and integrated DNS for the validation profile. Keep network addressing non-overlapping with host, VPN, and Docker ranges; document the chosen subnet/address in Compose comments or operator documentation.
- [x] Implement the designed forwarding path for non-authoritative Compose service names without changing existing clients' resolver configuration.
- [x] Add an operator helper to export only the public FreeIPA CA certificate for subsequent read-only consumer mounts. No production clients are attached to the validation network.
- [x] Add bounded, sanitized health/readiness checks for LDAP over TLS with server identity validation and Kerberos ticket acquisition for a validation service principal. Process existence alone must not indicate readiness.
- [ ] If Docker Desktop cannot start the selected image or the DNS forwarding design cannot preserve Compose service lookups, stop and document the incompatibility for design review; do not silently switch the selected architecture.

### Step 3 — Add scoped identity provisioning support

- [x] Extend the existing host provisioning entry point with an explicit FreeIPA membership subcommand that runs only against the isolated validation profile and uses a scoped provisioner keytab.
- [x] Add bootstrap for role groups, approved new identities, validation service principals/keytabs, and a dedicated FreeIPA service principal whose delegated rights target only the three role groups. The validation Hive principal is FQDN-qualified; active consumer compatibility remains a Unit 6 gate.
- [x] Write keytab files atomically with owner-only permissions, refuse to replace existing files, suppress secret/keytab output, and report sanitized failure categories.
- [x] Keep MIT provisioning behavior available for the existing active authority; the no-argument workflow remains unchanged, and this FreeIPA path does not overwrite or delete current keytabs, principals, or KDC database.
- [x] Preserve RustFS identity-provisioning and PostgreSQL role-provisioning branches and their invocation contract. Do not rotate RustFS writer S3 credentials.

### Step 4 — Add operator-controlled backup and cutover/rollback artifacts

- [x] Add operator documentation for a stopped-service backup of FreeIPA `/data`, the MIT KDC database, old keytabs, and matching client configuration as a coordinated restore set. Unit 6 owns guarded executable backup/cutover tooling and restore rehearsal because it executes the integrated authority transition.
- [x] Document preflight checks for required FreeIPA groups/identities/service principals, TLS, KDC ticket acquisition, DNS SRV/FQDN resolution, Docker service-name resolution, scoped provisioner readiness, and readable backup artifacts. Unit 6 implements executable go/no-go enforcement.
- [x] Provide an explicit, reviewable cutover procedure that stops MIT before FreeIPA becomes authoritative and switches dependent clients together. Unit 6 owns guarded executable cutover/rehearsal and must enforce the single-authority invariant.
- [x] Document the coordinated rollback path restoring MIT state, old keytabs, and matching client configuration together. Unit 6 implements/rehearses executable rollback. Preserve FreeIPA state and logs for diagnosis; never remove buckets, objects, or persistent volumes.
- [ ] Do not run backup, cutover, rollback, keytab replacement, or identity deletion against the live stack during Code Generation.

### Step 5 — Document the operator workflow and dependent-unit interfaces

- [x] Update `README.md` or the existing operations guide with isolated startup, required secret-file names (paths only), permissions, readiness inspection, backup inventory, cutover/rollback sequence, and known Docker Desktop/DNS limits.
- [x] Document each consumer's CA trust and keytab interface without switching its active mount/configuration in this unit.
- [x] Record the image digest, selected FQDN/network details, files changed, provisioning contract, and remaining Build and Test gates in the Unit 1 code summary.

### Step 6 — Conformance review and handoff

- [x] Review the generated changes against approved requirements and all Unit 1 designs; confirm the generation work did not modify MIT KDC files or active client configuration. This is a file-scope review only; runtime behavior remains for Build and Test.
- [ ] Confirm no secret values, runtime state, duplicate implementation files, or unrelated component changes were added to Git.
- [x] Create `aidlc-docs/current/construction/unit-1/code/code-summary.md` with changed paths, interfaces, operational behavior, explicit non-actions, and Build and Test verification items.
- [ ] Update this plan's checkboxes and `aidlc-docs/current/aidlc-state.md` as implementation steps are completed. No tests are added or run during Code Generation.

## Build and Test Gates

The following are deferred to the approved Build and Test stage: image pull/start and ARM64 runtime compatibility; digest verification; persistent state across stop/recreate; first-install behavior; LDAP TLS validation; integrated DNS and Compose DNS forwarding; loopback-only port exposure; secret mount permissions and log safety; isolated identity/group/keytab provisioning; backup inspection and isolated restore; single-authority cutover/rollback rehearsal; and confirmation that writer S3 credentials, production objects, and admin mapping remain unchanged.

## Scope Exclusions

- Do not switch the active KDC, change active client `krb5.conf`, replace production keytabs, or delete MIT principals/KDC state during Code Generation.
- Do not remove `user_a`/`user_b`, rotate RustFS credentials, modify buckets or data, or alter Hive/S3 authorization policy in this unit.
- Do not implement Ranger, StarRocks, Airflow, Jenkins, JupyterHub LDAP login, or per-user Spark ticket acquisition; dependent units own those changes.
- Do not introduce HA, replicas, external monitoring, automated backup services, or a new orchestration framework.

## Approval Gate

Review this complete plan. Explicit approval is required before application code, Compose configuration, identity provisioning, or operator documentation is changed.

**Status:** Approved by the user on 2026-10-27. Validation and identity provisioning code plus operator handoff are drafted. Runtime behavior, FreeIPA CLI semantics, TLS/DNS, and permission enforcement remain Build and Test gates. Unit 6 owns guarded executable cutover/rollback rehearsal. No services have been started and no tests have been added or run.
