# Unit 5 NFR Design — Native StarRocks LDAP Authorization

## Authorization path

FreeIPA authenticates the StarRocks login and owns role-group membership. The StarRocks LDAP Group Provider resolves the groups; native StarRocks RBAC maps external groups to roles and enforces catalog/database/table grants. StarRocks FE/BE then uses its own backend identity for HMS and RustFS. Direct Spark calls to RustFS continue to use the requesting Spark identity and RustFS IAM policy.

The implementation uses explicitly registered LDAP users bound to their DNs. StarRocks 4.1 documentation limits security-integration virtual users with native authorization; the implementation must not silently switch to that mode or add Ranger.

## Least privilege

| Group / role | Grants |
|---|---|
| Developers | SELECT on explicit production, development, and UAT Iceberg lists; INSERT only on development; SELECT on MVs in all three internal environment databases |
| Analysts | SELECT only on explicit production Iceberg database list and production internal MVs |
| Writers | SELECT and INSERT on the three explicit Iceberg lists; scoped MV CREATE/ALTER/REFRESH/DROP/SELECT in the three internal environment databases |
| Unknown or no mapped group | No data role |

No global grants or security-administration grants are generated. Environment database lists must be non-empty, valid, and pairwise disjoint. The sole DDL exception is narrowly scoped materialized-view management for `write-service-account` in the three approved internal environment databases; developer and analyst receive MV SELECT only. General database/table DDL and existing grants must be reviewed separately before production use. The writer's LDAP SQL password is distinct from its keytab and all SQL clients must use TLS.

Role groups must be mutually exclusive because StarRocks applies mapped roles together. Provisioning and periodic directory review enforce this condition; native role mappings do not provide deny-overrides for conflicting groups.

## Availability, freshness, revocation

LDAP login or group lookup failure must not add privileges. The group provider cache is configured explicitly; its actual refresh behavior, stale-data behavior, role removal in fresh sessions, and current-session behavior are measured in Build and Test. No latency or immediate-revocation SLA is claimed. A temporary LDAP outage may retain cached group data for the configured stale window; document the measured exposure window before production rollout.

## Secret and transport handling

- Use LDAPS and validate the FreeIPA CA/hostname for authentication and group lookups.
- Use a read-only LDAP lookup account; never use FreeIPA `admin`.
- Read LDAP bind and StarRocks admin credentials from owner-only files. Do not pass password values in command-line arguments, print SQL containing a secret, or include client errors in logs.
- StarRocks masks the LDAP provider secret in `SHOW CREATE GROUP PROVIDER`; still protect SQL input, connection logs, option files, backups, and audit output.
- Keep the StarRocks SQL admin registration and any role bootstrap operation separate from human data roles.

## Preservation and isolation

Bootstrap refuses to run unless Docker metadata identifies the exact disposable test FE and expected loopback SQL port. Test and production credentials, FE volumes, databases, and FreeIPA services are separate. The bootstrap creates/updates only its named provider, users, roles, and grants in that disposable FE. It does not revoke unrelated grants or touch the default FE.

## Verification gates

Verify LDAP login, group membership resolution, role/grant readback, database-scoped allow/deny, INSERT boundaries, absent/unknown group behavior, conflicting memberships, cache and revocation behavior, audit redaction, and unchanged production inventories. Also verify direct Spark/RustFS separately; StarRocks RBAC does not protect direct object-store access.
