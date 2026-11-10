# Unit 1 Code Generation Summary

## Scope

Adds an opt-in FreeIPA validation environment and operator-facing identity/cutover contracts. The active MIT KDC remains authoritative. Unit 1 isolated validation is complete; this work does not execute cutover or replace active client keytabs.

## Files and interfaces

- `docker-compose.yml`: isolated `freeipa-validation` profile and non-overlapping dedicated network; only loopback HTTPS is published; FreeIPA 4.13.4 AlmaLinux 9 base image is pinned to its digest and `/data` uses named volume `iceberg-poc-freeipa-validation-data-nss-patched2`. Prior partial volumes are retained.
- `infra/freeipa/patch-volatile-journal.py`: patches the upstream systemd init and journald configuration to keep command-line metadata in the container's volatile journal rather than persistent FreeIPA `/data`.
- `infra/freeipa/entrypoint.sh`: links the read-only installer-options secret into the FreeIPA volume at the upstream expected path without copying secret contents.
- `scripts/bootstrap-local.sh`: creates owner-only FreeIPA bootstrap files without displaying secrets.
- `scripts/freeipa-validation.sh`: operator `start`, `status`, and `stop` wrapper; `start` checks the configured Docker subnet for overlap.
- `infra/freeipa/check-network.py`: detects collisions against existing Docker IPAM ranges.
- `infra/freeipa/readiness.sh`: bounded LDAP TLS and Kerberos readiness probe.
- `scripts/export-freeipa-ca.sh`: exports and validates only the public CA certificate.
- `infra/freeipa/bootstrap-identities.sh`: one-time administrator bootstrap for the approved groups, users, isolated Hive/writer/StarRocks principals and keytabs, plus the dedicated `lakehouse-membership/ipa.lakehouse.local` principal. It explicitly avoids reusing FreeIPA's own HTTP server principal. It does not create human passwords or touch active MIT state.
- `infra/freeipa/set-role-membership.sh`: uses the dedicated scoped principal for allowlisted role-group membership changes only.
- `scripts/provision-identities.sh freeipa-membership ...`: explicit isolated FreeIPA membership subcommand; the original no-argument MIT/RustFS/PostgreSQL orchestration remains the default.
- `aidlc-docs/current/construction/unit-1/code/consumer-identity-interfaces.md`: downstream CA/keytab boundaries; validation keytabs are stored in the named volume under `/data/keytabs/`.
- `aidlc-docs/current/construction/unit-1/code/cutover-and-rollback-runbook.md`: backup inventory, go/no-go checks, cutover and coordinated rollback handoff for Unit 6.

## Runtime verification and deferred integration

The isolated bootstrap, approved role memberships, service keytabs, scoped positive/negative authorization boundaries, persistence, and replacement backup/restore have passed. The dedicated membership principal is `lakehouse-membership/ipa.lakehouse.local`; it must remain distinct from FreeIPA's server `HTTP/ipa.lakehouse.local` principal. Downstream JupyterHub/Hive/RustFS authentication and authorization, shared-network DNS, and coordinated client migration remain open for their dependent units. The validation Hive service uses `hive/hive-metastore.lakehouse.local@LAKEHOUSE.LOCAL`, while active clients currently expect `hive/hive-metastore@LAKEHOUSE.LOCAL`; matching and migration remain Unit 6 work.

## Explicit non-actions

- The first isolated FreeIPA startup on Rancher Desktop failed during template population on a host bind mount. The approved storage revision switches to a named Docker volume; the bind-mount data remains untouched for diagnosis.
- Named-volume startup exposed host cgroup memory-path and Docker DNS forwarder validation issues; these were handled with the pinned image's `--skip-mem-check` option and a configurable external DNS forwarder. A Dogtag CA-agent PKCS#12 import failure was resolved with the JSS importer fallback and CLI-based RA certificate issuance described above.
- The initial protected backup persisted installer passwords in systemd journal metadata. Both validation-only passwords were rotated; the old archive was removed after a replacement backup without the journal was restored in a separate named volume. Journaling is now volatile and was verified not to modify the persistent journal file.
- No MIT KDC state, active client configuration, principal, or keytab was changed.
- No RustFS S3 credential, bucket, object, administrator mapping, `user_a`/`user_b` account, or workspace was changed.
- No downstream consumer was attached to the isolated FreeIPA network.

## Build and Test gates

Unit 1 isolated Build and Test passed for Rancher Desktop ARM64 startup, readiness, TLS/Kerberos, local DNS and external forwarding, persistence, scoped identity boundaries, service keytabs, volatile journaling, and protected backup/restore. Unit 6 owns shared-network DNS, client cutover, and integrated Hive/Spark/Airflow/RustFS/StarRocks authorization and rollback rehearsal.
