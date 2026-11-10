# Application Components — Central Identity and Environment Access

## Identity and policy plane

### FreeIPA

Authoritative directory for human users, role groups, service users, Kerberos principals, and group membership. It authenticates JupyterHub over TLS/LDAP and issues Kerberos credentials. FreeIPA group membership is the canonical human role assignment; it does not directly authorize S3 requests.

### Identity and policy provisioner

An explicitly invoked, idempotent reconciliation job. It reads the version-controlled role policy document and FreeIPA identities/group membership, then reconciles RustFS IAM identities, group membership, and policies. It verifies resulting policies and reports drift/failure. It must not print access keys, keytabs, passwords, or directory bind credentials.

Role-to-path policy definitions belong in a declarative file in the identity-provisioner source tree and are changed through Git review. Routine user grant/revoke operations change FreeIPA group membership and run or trigger reconciliation; they do not require editing policy documents.

## Data and execution plane

### RustFS

Stores objects in `lake` (production), `lake-dev` (development), and `lake-uat` (UAT). Its IAM users/groups and S3 policies enforce object-level read/write boundaries. Human Spark sessions use a distinct RustFS identity for the signed-in user; ETL keeps the existing `write-service-account` identity.

### Hive Metastore

Stores catalog metadata in PostgreSQL and serves metadata to Spark and StarRocks over Thrift. It uses Kerberos authentication and the configured Hive Metastore authorization provider. The design retains the current storage-based metastore authorization approach only if its checks are proven to work against the configured S3A/RustFS locations. No HiveServer2 is introduced in this design.

### Spark

Spark notebook sessions execute as the requesting human user for Kerberos and object-storage authorization. Airflow ETL remains non-interactive and uses the existing writer service identity. Spark access is independently checked at the metastore and RustFS; StarRocks roles do not authorize direct Spark requests.

### JupyterHub

Authenticates human users against FreeIPA LDAP over TLS, allows only approved human groups, and starts isolated single-user notebook containers. It supplies only that user’s runtime identity material to that user’s container. The writer service identity is never mounted into human notebook containers.

### StarRocks

Optional SQL analytics engine. Uses its own service identity to read HMS metadata and RustFS objects. Its LDAP Group Provider resolves FreeIPA role groups; native StarRocks roles/grants authorize SQL queries. LDAP passwords and group membership remain in FreeIPA. StarRocks service credentials do not replace SQL-user authorization.

## Administration and operations

### Platform administrator

The existing `admin` identity retains platform administration separately from data roles.

### Operator workflow

FreeIPA admin manages users and group membership. Git review manages RustFS role-policy definitions. The reconciler applies and verifies RustFS state. StarRocks administration manages SQL role grants; bootstrap maps FreeIPA groups to native StarRocks roles. Runtime provisioning and verification never change or delete existing production objects.
