# Unit 1 Consumer Identity Interfaces

This document describes the intended FreeIPA material boundary for downstream units. Unit 1 validation remains isolated; these interfaces do not change active mounts or the MIT KDC.

| Consumer | Directory trust | Kerberos material | Owner |
|---|---|---|---|
| Hive Metastore | FreeIPA CA certificate, read-only; LDAP/KDC FQDN | Validation keytab for `hive/hive-metastore.lakehouse.local@LAKEHOUSE.LOCAL`; active client principal migration is Unit 6 | Unit 3 / cutover Unit 6 |
| Spark and Airflow Spark jobs | FreeIPA CA certificate only if they make LDAP calls; Kerberos realm/KDC configuration | Writer service keytab only for ETL jobs; human notebook keytabs are per-user and belong to Unit 4 | Unit 4 / cutover Unit 6 |
| StarRocks FE/BE | FreeIPA CA certificate for Ranger UserSync if configured | StarRocks service keytab | Unit 5 / cutover Unit 6 |
| RustFS reconciler | Read-only LDAP identity/group lookup over TLS, when enabled | No Kerberos keytab unless the chosen RustFS integration requires it | Unit 2 |
| Ranger UserSync | FreeIPA CA certificate and a read-only LDAP bind identity, if required by the selected UserSync version | No Kerberos keytab in the selected LDAP path | Unit 5 |
| JupyterHub | FreeIPA CA certificate and LDAP endpoint | No shared keytab; per-user credential and ticket lifecycle is Unit 4 | Unit 4 |

## Keytab handling contract

- Validation keytabs are separate files per principal under `/data/keytabs/` in the dedicated FreeIPA Docker volume, mode `0600`. Unit 6 must export and stage accepted keytabs into existing consumer credential locations as individual files with owner-only permissions and read-only mounts. Never mount an administrator or provisioner keytab into workload containers.
- Use temporary protected staging files and atomic rename when installing generated keytabs. Check principal/keytab compatibility before replacing a current file; preserve the MIT-issued version as rollback material until Unit 6 acceptance.
- Validation keytab filenames are `hive-metastore.keytab`, `write-service-account.keytab`, and `starrocks.keytab`. The Hive validation principal uses `HIVE_SERVICE_FQDN` (default `hive-metastore.lakehouse.local`) and does not match the currently configured short-host MIT principal. Unit 6 must update the Hive service hostname and all clients together after DNS/principal verification; do not copy this keytab into the active path early.
- The RustFS writer S3 access key/secret is not a Kerberos keytab and must remain unchanged.

## Directory provisioning boundary

FreeIPA bootstrap administrator use is restricted to initial setup and privilege delegation. Routine role membership reconciliation authenticates as a distinct scoped FreeIPA service principal. Its permissions target the `member` attribute on the three approved role groups; it cannot administer FreeIPA, change passwords, manage unrelated groups, or issue arbitrary service keytabs. Verify the actual permission enforcement against the selected FreeIPA image in Build and Test before enabling downstream synchronization.
