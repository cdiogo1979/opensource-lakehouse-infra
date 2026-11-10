# Unit 5 Functional Design — Domain Entities

## Entities

### DirectoryUser

FreeIPA identity that authenticates to StarRocks using its directory password.

| Attribute | Meaning |
|---|---|
| username | Stable login identifier shared by FreeIPA and StarRocks |
| user DN | FreeIPA LDAP distinguished name registered for LDAP authentication and group lookup |
| enabled | Whether FreeIPA allows authentication |
| roleGroups | Canonical `lakehouse-*` memberships |
| identityType | Human or non-interactive service identity |

StarRocks stores an explicit user registration and DN for the selected native-RBAC flow. It does not store the FreeIPA password.

### RoleGroup and StarRocksRole

| FreeIPA group | StarRocks role | Access |
|---|---|---|
| `lakehouse-developers` | `lakehouse_developer` | Read all configured environments; INSERT only into configured development databases |
| `lakehouse-analysts` | `lakehouse_analyst` | Read configured production databases only |
| `lakehouse-writers` | `lakehouse_writer` | Read and INSERT in configured environments |

StarRocks' LDAP Group Provider resolves group membership; `GRANT ROLE ... TO EXTERNAL GROUP ...` assigns role privileges. Groups must be mutually exclusive because the effective permissions are the union of mapped roles.

### CatalogDatabaseScope

Explicit environment-to-StarRocks external catalog database mapping supplied to bootstrap. Each database appears in one environment list only. Access is granted to listed database tables/views, not to all databases in a catalog.

### StarRocksSession

Authenticated native StarRocks user session using FreeIPA LDAP authentication.

| Attribute | Meaning |
|---|---|
| principal | Registered StarRocks username / FreeIPA login |
| user DN | Explicit LDAP DN associated with the user |
| groups | FreeIPA groups resolved by the LDAP Group Provider |
| activeRoles | StarRocks roles inherited through external group mappings |

Group/cache changes apply according to observed FE behavior and current session state; no instant revocation guarantee is implied.

### StarRocksStorageIdentity

FE/BE identity for backend HMS and RustFS operations after SQL authorization. It remains separate from the login user and is not exposed to clients.

## Relationships

```text
FreeIPA DirectoryUser ── LDAP authentication ──> StarRocks user registration
DirectoryUser ── group membership ──> RoleGroup
RoleGroup ── external-group grant ──> StarRocksRole
StarRocksSession + role grants ──> native authorization decision
        │ allow
        v
StarRocksStorageIdentity ──> Hive Metastore / RustFS

Direct Spark user ── own RustFS credentials/policy ──> RustFS
```
