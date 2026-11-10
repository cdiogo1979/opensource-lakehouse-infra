# Unit 4 Functional Design — Business Logic Model

## Purpose and boundary

This unit specifies how FreeIPA human identities enter JupyterHub and how a spawned notebook obtains the user's own Spark credentials. FreeIPA groups choose the data role; RustFS remains the data-plane authority for direct Spark object operations. Hub administrator status is a separate platform privilege. This design does not change runtime configuration or perform the Unit 6 Kerberos-authority cutover.

## Trust boundaries and actors

1. **FreeIPA** stores canonical human accounts and the `lakehouse-developers` and `lakehouse-analysts` groups. It answers LDAPS bind and membership lookups. `lakehouse-writers` is explicitly excluded from interactive access.
2. **JupyterHub** authenticates the submitted user against FreeIPA, authorizes an allowed group, and asks DockerSpawner to create that user's isolated notebook. It acts as the trusted credential-mount broker and must use a provisioned identity registry rather than accepting host paths from the user.
3. **Notebook container** runs as an unprivileged UID, receives only its own read-only keytab and RustFS credential files, obtains its Kerberos ticket into a private tmpfs cache, and launches JupyterLab/Spark.
4. **Active MIT KDC (transition only)** remains the sole KDC for the current HMS/Spark services until Unit 6. FreeIPA LDAP authentication is not itself a ticket and does not make FreeIPA the active Kerberos authority.
5. **Hive Metastore** authenticates Spark's Thrift requests with the notebook's Kerberos ticket. **RustFS** independently authorizes each S3 request using the matching user's S3 credentials.
6. **Workspace volume** persists user files across normal notebook stops. It is separate from ephemeral ticket state and credential mounts.

## Authentication and spawn sequence

```text
Browser
  -> JupyterHub: username + password over the configured protected UI transport
  -> FreeIPA LDAPS: bind and resolve canonical account + group membership
  <- JupyterHub: allow only developer group, analyst group, or explicit admin account
  -> pre-spawn authorization: reject missing/conflicting roles and disabled users
  -> identity registry: resolve approved workspace + own keytab + own RustFS key pair
  -> DockerSpawner: read-only credential mounts + persistent workspace + private tmpfs
  -> notebook entrypoint: kinit with that user's keytab into tmpfs; verify active principal
  -> Spark: HMS SASL as the user and RustFS S3 requests with that user's S3 identity
```

The authenticator should use direct user bind and a narrowly scoped search/group lookup identity only if FreeIPA's directory configuration requires it; any service bind secret must be a protected secret file and read-only to the Hub. Configure the FreeIPA CA explicitly and require hostname verification. The Hub can be attached only to the required internal FreeIPA validation/service network; the FreeIPA web UI's localhost redirect workaround is unrelated to the LDAPS endpoint. No public LDAP exposure or TLS verification bypass is allowed.

The authenticator returns the resolved group DNs as server-side authentication state. Enable encrypted auth-state storage only with a protected, stable JupyterHub crypt key. Do not store the submitted password in auth state or Hub database. The pre-spawn hook maps exact configured group DNs to role names, rejects role conflicts, and independently confirms the account is still enabled and authorized before using the registry entry.

## Role resolution

| Identity/group result | Hub login | Notebook spawn | Data identity |
|---|---|---|---|
| Exactly one `lakehouse-developers` membership | Allow | Allow if explicit credential registry entry is complete | `developer-user`'s own keytab and RustFS credentials |
| Exactly one `lakehouse-analysts` membership | Allow | Allow if explicit credential registry entry is complete | `analyst-user`'s own keytab and RustFS credentials |
| Explicit `admin` account, valid FreeIPA auth | Allow; retain Hub admin privileges | Allow through the admin's own registry entry | Existing `admin` keytab and RustFS credentials; platform privilege is separate |
| `lakehouse-writers`, no data role, multiple data roles, unknown group, disabled/missing user | Deny | Deny | None |

The current approved identity set is `developer-user`, `analyst-user`, and `admin`; `write-service-account` is non-interactive. The role groups are the source of authorization, while a strict provisioning registry ensures that a group grant alone cannot cause arbitrary host mounts. Supporting additional group members requires the identity/RustFS provisioning workflow to add matching per-user assets and registry data before access is enabled.

## Kerberos transition behavior

The present functional transition intentionally separates login and ticket issuance: FreeIPA authenticates the password and supplies group membership; the existing MIT KDC issues the user's ticket from that user's per-user keytab. Canonical usernames and principal names must match exactly in `LAKEHOUSE.LOCAL`. This preserves the active HMS principal trust without treating the independent FreeIPA KDC database as a second authority. It also means FreeIPA password disablement alone does not invalidate a MIT keytab, so account/group revocation must stop running notebook servers and remove/disable the corresponding ticket/keytab path through the separately controlled provisioning workflow.

At Unit 6 cutover, the coordinated migration reissues human and service keytabs under FreeIPA, updates all dependent services and clients, validates the same principal names, and only then makes FreeIPA the sole KDC. Unit 4 must not change the KDC alias, realm routing, HMS principal, or service keytabs.

## Credential and data flow

- The identity registry is authoritative for the mapping from canonical account to exact host-side files and workspace volume. It is provisioning-owned and not user-editable.
- The Hub validates registry paths against the configured credential root and mounts only the matched user's files read-only. It never interpolates an untrusted username into a path.
- The notebook entrypoint runs `kinit -kt` for the expected principal, checks `klist` for that same principal, and aborts startup on mismatch or failure.
- `KRB5CCNAME` points into per-container tmpfs. Keytab mounts remain read-only; the ticket cache does not enter the home directory or persistent volume.
- Spark presents its user ticket to the HMS and its matching S3 credentials to RustFS. A successful metadata request does not imply object access. Every query succeeds only if the RustFS request is allowed under the user's bucket policy.
- Spark/RustFS failures never trigger a service-account retry. The writer identity remains available only to approved ETL workloads.

## Stop, revocation, and persistence

Normal server stop removes the container while preserving the named user workspace. This destroys the in-container tmpfs ticket cache. A role removal or account disable blocks future login/spawn after a fresh FreeIPA check. An operator-controlled revocation action must additionally stop an active server; the implementation must record request and completion times and test the end-to-end interval. Do not promise immediate active-session revocation from LDAP group edits alone.

The existing admin volume remains mapped to `admin`. New named volumes for developer and analyst are distinct. No legacy user volume is automatically renamed, copied, mounted, or deleted. Workspace cleanup requires a separate retention decision.

## Failure behavior

| Failure | Result |
|---|---|
| FreeIPA LDAPS unavailable, invalid CA, invalid bind, unresolved account, or group lookup error | Login denied; no stale/default role |
| Missing/disabled account, no approved role, role conflict, or writer identity | Login/spawn denied |
| Missing/unsafe credential registry entry or any missing user credential file | Spawn denied before Docker container creation |
| kinit failure or principal mismatch | Notebook startup fails; no Spark session and no alternate identity |
| RustFS 403 or missing caller credentials | Spark object query fails under caller identity; no writer/admin fallback |
| KDC/HMS/RustFS unavailable | Request/startup fails closed; no broader credentials or bypass |
| Revocation while a container is running | Revocation workflow stops server; future spawn denied; completion measured |

## Traceability

| Requirement | Design coverage |
|---|---|
| FreeIPA interactive authentication and role groups | LDAPS login sequence, role resolution, U4-R1–R5 |
| Writer excluded from JupyterHub | Explicit deny in role table and U4-R3 |
| Per-user Kerberos flow without password persistence | User keytab, tmpfs ticket cache, no password in auth state; U4-R6–R13 |
| RustFS role enforcement from Jupyter/Spark | Caller-matched S3 credential path; no service fallback |
| Admin preserved | Explicit admin allowlist and current workspace mapping; U4-R4, U4-R16 |
| Revocation and persistence | Stop/revocation workflow and named volume lifecycle; U4-R15–R18 |
| FreeIPA sole KDC after staged cutover | MIT interim behavior and Unit 6 transition boundary |

## Technical references

- JupyterHub LDAPAuthenticator supports TLS settings, allowed LDAP groups, and group information in authentication state: [LDAPAuthenticator](https://github.com/jupyterhub/ldapauthenticator).
- JupyterHub supports encrypted authentication state when configured with a crypt key: [JupyterHub authentication](https://jupyterhub.readthedocs.io/en/stable/reference/authenticators.html).
- FreeIPA documents LDAP access and directory layout: [FreeIPA LDAP](https://www.freeipa.org/page/HowTo/LDAP.html).
- DockerSpawner supports pre-spawn hooks, volume mounts, and container cleanup: [DockerSpawner API](https://jupyterhub-dockerspawner.readthedocs.io/en/latest/api/index.html).
- MIT Kerberos documents keytab-based ticket acquisition: [kinit](https://web.mit.edu/kerberos/krb5-latest/doc/user/user_commands/kinit.html).
