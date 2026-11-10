# Unit 1 FreeIPA Backup, Cutover, and Rollback Runbook

This is an operator handoff for a future maintenance window. It is not a command sequence to run during Code Generation. Unit 6 owns execution and integrated acceptance. Do not start FreeIPA on the active network, stop the MIT KDC, replace a client keytab, or change production identity configuration as part of this runbook draft.

## Required coordinated backup set

Create and inspect these artifacts before any authority switch:

1. FreeIPA `/data` from a cleanly stopped validation instance, copied to owner-only storage. Preserve the whole state directory and file metadata.
2. The complete MIT KDC database and configuration from the existing `kerberos-kdc-data` volume, copied while the KDC is stopped.
3. Existing Kerberos keytabs from `.runtime/credentials/keytabs/`, including the current KDC provisioning material and service keytabs. Keep files mode `0600` in the backup.
4. The matching client configuration (`infra/kerberos/krb5.conf`, generated Hive configuration, and service Compose/environment settings) captured from the same point as the MIT database and keytabs.
5. A secret-free inventory of active principal names, service consumers, bucket names, the RustFS writer access-key identifier, production bucket/object preservation references, and the existing administrator mapping. Do not record S3 secret values or keytab contents.

Store the archive under an operator-controlled, access-restricted backup location outside Git and outside any consumer container. Record archive paths, timestamps, file counts, and checksums without printing credential material. Test archive readability and perform restore rehearsal in an isolated copy before a production maintenance window.

## Go/no-go checklist

- FreeIPA validation is healthy for LDAPS with CA and hostname verification and for Kerberos ticket acquisition.
- Required role groups and users exist, and their memberships match approved intent.
- The scoped provisioning identity can perform only the approved operations; an administrative or arbitrary keytab operation is denied.
- The complete current principal inventory has been matched to FreeIPA principal names; all required new service keytabs authenticate in isolated clients.
- FreeIPA DNS records and SRV lookups resolve, and Docker service-name forwarding still works.
- Every backup artifact above is readable and checksummed; restore rehearsal succeeded without touching production volumes.
- The writer RustFS S3 key identifier, `lake` production data, and administrator component mapping are recorded for post-change comparison.
- An operator has a maintenance window, stop-work trigger, service restart order, and rollback owner.

Any failed or unknown check is a no-go. Do not allow two independent KDC databases for `LAKEHOUSE.LOCAL` to serve clients concurrently.

## Cutover sequence (Unit 6 execution only)

1. Announce maintenance, stop new jobs and notebook sessions, and capture the pre-cutover inventory.
2. Stop dependent identity clients, then stop MIT KDC service. Confirm it no longer serves the realm.
3. Attach/activate FreeIPA on the reviewed active identity network and stable KDC endpoint. Apply the reviewed realm, DNS, TLS CA, and client endpoint configuration as one change.
4. Install FreeIPA-issued service keytabs atomically into their intended consumers with read-only mounts. Keep old MIT keytabs in the protected backup, not active mounts.
5. Start consumers in the approved dependency order. Validate ticket acquisition and Hive/Spark, Airflow writer, StarRocks, and LDAP consumers.
6. Compare preservation checks and accept only after all critical service and access tests pass. Keep the MIT backup sealed through the agreed acceptance period.

## Rollback sequence

On a critical authentication, TLS, DNS, Hive/Spark, or service failure, stop forward rollout. Stop dependent clients and FreeIPA so it no longer serves the realm. Restore the MIT KDC database, its matching old keytabs, and matching client configuration together; start MIT and then clients. Verify writer S3 credentials, production data, and admin mapping remain unchanged. Preserve FreeIPA state and logs for diagnosis. Never delete or recreate RustFS buckets, object-store data, or persistent volumes as a rollback action.

Do not disable `user_a`/`user_b` or remove their workspaces as part of this authority cutover. Unit 6 may retire them only after the new role matrix has passed and with its own approval gate.
