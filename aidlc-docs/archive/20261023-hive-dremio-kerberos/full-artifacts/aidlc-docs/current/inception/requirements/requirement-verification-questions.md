# Requirements Verification Questions

Please answer each question by entering a choice after `[Answer]:`. Choose `X` and add details if the listed choices do not fit.

## Question 1 — Hive deployment shape
What should provide the Hive 3.x catalog?

A) A standalone Hive Metastore service in Docker Compose; no HiveServer2

B) Hive Metastore plus HiveServer2 in Docker Compose

C) An existing Hive 3.x metastore outside this Compose project

X) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 2 — Hive version and metadata database
Which Hive 3.x version and metastore database should the PoC target?

A) Select a compatible Hive 3.x release and use PostgreSQL in Compose

B) Use a Hive version and database I will specify

C) Connect to an existing metastore database with settings I will provide

X) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 3 — Kerberos KDC and realm
Where should Kerberos identities come from?

A) Add a disposable local KDC to Docker Compose for the PoC

B) Connect to an existing KDC/realm; I will provide realm and connectivity details

C) Use an existing corporate/organizational realm and document the required external setup without containerizing a KDC

X) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 4 — User authentication and impersonation flow
How should a user identity reach Dremio and be used for impersonation?

A) Authenticate users to Dremio with Kerberos; Dremio accesses Hive as a service principal and impersonates the authenticated user

B) Authenticate users to Dremio with Dremio-local accounts; map each Dremio username to a Kerberos/Hadoop user for impersonation

C) Demonstrate Kerberos-authenticated Spark access and Hive-side proxy-user impersonation, while Dremio uses a service identity

X) Other (please describe the intended end-to-end identity flow after `[Answer]:` below)

[Answer]:A

## Question 5 — Services in scope for Kerberos
Which services must use Kerberos in this PoC?

A) Dremio to Hive Metastore only; keep RustFS on S3 access keys

B) Dremio and Spark to Hive; keep RustFS on S3 access keys

C) Dremio, Spark, and RustFS/object storage must all participate in identity-based authentication

X) Other (please describe after `[Answer]:` below)

[Answer]:C

## Question 6 — Impersonation authorization
How should the PoC constrain which users a service can impersonate?

A) Configure Hive Hadoop proxy-user rules with explicit allowed users/groups and hosts

B) Allow a broad local PoC user/group range and document that it is development-only

C) Use existing organizational Hadoop proxy-user policy; I will provide its constraints

X) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 7 — Success scenario
What should count as a successful demonstration?

A) Spark creates/loads Iceberg tables through Hive Metastore and Dremio queries those tables

B) The above, plus two users with different identities can query and Hive logs/audit evidence shows the effective impersonated user

C) The above, plus a negative authorization check proves a user outside the allowed proxy-user policy is rejected

X) Other (please describe after `[Answer]:` below)

[Answer]:C

## Question 8 — Secret and Kerberos material handling
How should keytabs, principals, and passwords be supplied in the local PoC?

A) Use ignored local files mounted read-only; provide examples containing placeholders only

B) Generate disposable test principals/keytabs as part of a local KDC container initialization flow

C) Use an external secrets system or existing keytab distribution process; I will describe it

X) Other (please describe after `[Answer]:` below)

[Answer]:B

## Question 9 — Security Baseline extension
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)

B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)

X) Other (please describe after `[Answer]:` below)

[Answer]:B

## Question 10 — Property-Based Testing extension
Should property-based testing (PBT) rules be enforced for this project?

A) Yes — enforce all PBT rules as blocking constraints (recommended for projects with business logic, data transformations, serialization, or stateful components)

B) Partial — enforce PBT rules only for pure functions and serialization round-trips (suitable for projects with limited algorithmic complexity)

C) No — skip all PBT rules (suitable for simple CRUD applications, UI-only projects, or thin integration layers with no significant business logic)

X) Other (please describe after `[Answer]:` below)

[Answer]:B

## Question 11 — Resiliency Baseline extension
Should the resiliency baseline be applied to this project?

The baseline provides directional design-time guidance for fault tolerance, availability, observability, and recovery. It does not certify production readiness or guarantee availability targets.

A) Yes — apply it as directional best practices

B) No — skip it for this PoC

X) Other (please describe after `[Answer]:` below)

[Answer]:B
