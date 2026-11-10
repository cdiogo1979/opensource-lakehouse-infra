# Unit 4 Functional Design — Domain Entities

## Identity and authorization entities

| Entity | Meaning | Key attributes and invariants |
|---|---|---|
| `DirectoryAccount` | Human account authenticated by FreeIPA | Canonical username, enabled/locked state, LDAP identity; login password is validated by FreeIPA and is never retained by JupyterHub. |
| `RoleGroup` | FreeIPA group that grants a notebook data role | Exact supported groups: `lakehouse-developers`, `lakehouse-analysts`; `lakehouse-writers` is ETL-only and denied for interactive access. |
| `HubAdministrator` | Explicit platform administrator identity | `admin` remains separately allowlisted and retains its current JupyterHub admin mapping. Admin status does not arise from developer/analyst group membership. |
| `AuthenticatedPrincipal` | Result of a successful FreeIPA login | Canonical username, enabled status, resolved group DNs, authentication time; no password or credential bytes. |
| `NotebookRoleDecision` | Per-login and per-spawn authorization outcome | Principal, exact role set, decision time, allow/deny reason category. Missing, unknown, or conflicting role is deny. |

## Provisioned identity entities

| Entity | Meaning | Key attributes and invariants |
|---|---|---|
| `NotebookIdentityRegistryEntry` | Provisioning-owned mapping required before spawn | Canonical username, role, exact credential file references, exact workspace volume, expected Kerberos principal, enabled state. Not user-writable; no arbitrary path construction. |
| `KerberosCredential` | User-specific keytab used to obtain a ticket | Principal and protected file reference; one identity per keytab; mounted read-only only into that user's container. No password value is stored. |
| `KerberosTicketCache` | Short-lived ticket state for one container | Expected user principal, location in private tmpfs, container lifecycle. Never persisted to workspace or shared between users. |
| `RustFSCredentialPair` | Per-user S3 access and secret key files | User-matched identity and protected file references; read-only mounts; scope enforced by RustFS policy. Writer/admin keys are excluded from other users. |
| `WorkspaceVolume` | Persistent user notebook files | One named volume per canonical account; survives normal stop/restart; never contains keytabs or ticket cache. Renames/deletion require separate reviewed migration/retention actions. |

## Runtime and service entities

| Entity | Meaning | Constraints |
|---|---|---|
| `JupyterHub` | Authentication and server orchestration service | FreeIPA LDAPS with trusted CA; encrypted auth state; fresh authorization before spawn; only explicit Hub admin is administrator. |
| `NotebookServer` | Per-user container managed by DockerSpawner | Unprivileged runtime user; exactly one registry entry; own credential mounts only; private ticket tmpfs; distinct persistent workspace. |
| `FreeIPAEndpoint` | Internal LDAP/TLS endpoint used by Hub | Stable internal hostname, LDAPS, certificate hostname and CA verification, bounded connection/search timeouts; never browser localhost URL. |
| `ActiveKDC` | KDC used for notebook/HMS Kerberos during transition | MIT KDC remains sole active KDC until Unit 6 coordinated cutover; FreeIPA LDAP authentication must not be confused with FreeIPA KDC ticket issuance. |
| `HiveMetastore` | Kerberos-protected metadata endpoint | Receives the notebook's expected user principal; its own service credentials remain isolated. |
| `RustFS` | S3-compatible object store enforcing data policy | Receives the notebook's user-specific S3 identity; independently authorizes reads/writes for each request. |
| `RevocationAction` | Controlled invalidation of an active notebook identity | Subject, operator/trigger, requested/completed timestamps, server-stop result, safe correlation ID; completion includes ticket-cache destruction. |

## Relationships

```text
DirectoryAccount ──member of──> RoleGroup ──authorizes──> NotebookRoleDecision
DirectoryAccount ──maps through──> NotebookIdentityRegistryEntry
NotebookIdentityRegistryEntry ──selects──> KerberosCredential
NotebookIdentityRegistryEntry ──selects──> RustFSCredentialPair
NotebookIdentityRegistryEntry ──selects──> WorkspaceVolume
DockerSpawner ──creates──> NotebookServer ──owns──> KerberosTicketCache
NotebookServer ──Kerberos request──> ActiveKDC ──ticket used with──> HiveMetastore
NotebookServer ──S3 request with user key──> RustFS
RevocationAction ──stops──> NotebookServer ──destroys──> KerberosTicketCache
```

## State invariants

- One canonical account resolves to one supported data role or to the separate explicit admin mapping; conflicting role groups deny access.
- Every spawned notebook has a complete, verified registry entry before Docker create.
- A container cannot access another user's credential files through mounts or shared ticket cache.
- The workspace is persistent; credentials and tickets are not stored in it.
- FreeIPA authentication, Kerberos ticket issuance, and RustFS S3 authorization are separate operations and must use matching user identities.
- Role membership alone does not provision RustFS keys or a Kerberos keytab; missing provisioned assets keep spawn denied.
- JupyterHub administrator authority is separate from lakehouse data roles; the ETL writer is not interactive.
- Revocation of a running server is incomplete until the container stops and ephemeral ticket state is gone.
