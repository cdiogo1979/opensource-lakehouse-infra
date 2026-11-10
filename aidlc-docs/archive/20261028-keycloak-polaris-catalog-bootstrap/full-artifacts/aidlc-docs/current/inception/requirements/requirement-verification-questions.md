# Requirements Clarification Questions

The reverse-engineering review is accepted. Please answer each question by entering a letter or a short custom answer after `[Answer]:`. Recommendations are marked. These answers define the first platform-admin journey for creating the `default` data product.

## Question 1 — How does the platform admin create a data product?
What is the intended interaction for the first release?

A) Run a documented, idempotent bootstrap CLI/script (Recommended for this infrastructure-first increment)

B) Use a platform-admin web UI that calls service APIs

C) Use the native Keycloak, Polaris, and RustFS admin interfaces separately

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 2 — Which environments does one data product create?
Should creating `default` create the matching catalog, namespace/database, and bucket in all three environments?

A) Yes: `lakehouse.default_lh` + `bucket-default`, `lakehouse-dev.default_lhdev` + `bucket-default-dev`, and `lakehouse-uat.default_lhuat` + `bucket-default-uat` (Recommended)

B) Create production only; create dev and UAT separately

C) Create only the environment selected by the admin each time

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 3 — What do the requested “databases” mean in Polaris?
Polaris catalogs contain namespaces; clients may call a namespace a database or schema. Should each requested name be the top-level namespace in its matching catalog?

A) Yes: one namespace per catalog using the exact names in Question 2 (Recommended)

B) Create a shared namespace name such as `default` in each catalog and keep the requested names as client-side database aliases

C) Use an additional namespace hierarchy under each catalog

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 4 — What access should each role receive?
Recommended starting matrix carries forward the previous project intent. Choose whether it matches the new data-product journey.

A) Developer: read all three; write dev only. Analyst: read production only; no writes. Writer: read/write all three. Owner: manage product objects and grants in all three (Recommended)

B) Developer: read/write dev only. Analyst: read production only. Writer: read/write all three. Owner: manage all three

C) Use the matrix in A, but limit the owner role to one selected environment per product

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 5 — What does “owner” mean?
Should `role-default-owner` grant product-level ownership in Polaris/RustFS while remaining separate from Keycloak realm administration and object-store root access?

A) Yes; owner manages the product’s data/catalog grants, but is not Keycloak realm admin or RustFS root (Recommended)

B) Owner is a full platform administrator across Keycloak, Polaris, and RustFS

C) Create separate platform-admin and data-product-owner roles; retain the four requested data roles as product roles

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 6 — How should the writer role be represented?
Spark/Airflow automation needs a non-interactive identity. A Keycloak group alone does not provide a process with credentials.

A) Create the `role-default-writer` Keycloak group and a dedicated writer service identity assigned to it; grant that identity read/write across all three products (Recommended)

B) Create only the group; operators will configure a separate service identity later

C) Use a Keycloak confidential client/service account as the writer identity, with no human group membership

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 7 — Who creates individual users and assigns roles?

A) Platform admin creates the four groups during product creation; users are provisioned separately and assigned to groups in Keycloak (Recommended)

B) The data-product creation flow also creates named human users and assigns them to groups

C) Users self-register and request group membership for owner approval

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 8 — Which authentication flow should the bootstrap support?
Keycloak can authenticate people, while Spark/Airflow and object storage need service-to-service credentials. Polaris and RustFS enforce their own authorization policies.

A) Keycloak OIDC for human web login; service identities use non-interactive OAuth/STS where supported, with scoped credentials as a fallback (Recommended)

B) Keycloak username/password for every client, including Spark and S3

C) Keep Kerberos for Spark/Hadoop and use Keycloak only for browser login

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 9 — Should MIT Kerberos remain?
FreeIPA was an LDAP/identity source, but the active KDC is a separate MIT Kerberos service. Keycloak does not issue Kerberos tickets.

A) Keep MIT Kerberos for existing Kerberos-dependent Spark/Hadoop integrations until a separately verified OAuth migration is complete (Recommended)

B) Remove MIT Kerberos in this intent and migrate every dependent component to non-Kerberos authentication

C) Keep Kerberos only for a named subset of services; describe which ones

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 10 — What test table should be created?
What should the bootstrap create in each of the three namespaces to prove catalog and storage access?

A) `bootstrap_smoke_test` with a small deterministic schema and one sample row, stored under that environment’s bucket (Recommended)

B) An empty Iceberg table; a separate test performs inserts

C) A configurable table name/schema supplied by the platform admin

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 11 — Which existing services are in this intent’s scope?
The core journey needs Keycloak, Polaris, and RustFS. The current project also includes Spark, JupyterHub, Airflow, Jenkins, and optional StarRocks.

A) Deliver the full end-to-end platform now: migrate and verify Spark, JupyterHub, Airflow, and StarRocks; retain Jenkins and RustFS; remove FreeIPA and Hive

B) First deliver only the platform-admin data-product journey; defer other client integrations until later (Recommended for the requested staged user journey)

C) Integrate only the specific clients named below and defer the rest

X) Other (please describe after [Answer]: tag below)

[Answer]:B

## Question 12 — What should happen if a named resource already exists?
You said catalogs, databases, and buckets may be freshly created and no migration is needed. Choose safe behavior for reruns or collisions.

A) Create missing resources, validate matching existing resources, and fail on conflicting resources; never delete data automatically (Recommended)

B) Delete/recreate all named resources and their data on every bootstrap run

C) Require an explicit `--reset` option for destructive recreation; default runs validate and preserve existing resources

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 13 — Where should Polaris metadata persist?
Polaris needs its own durable metadata store; it must not use the old Hive schema.

A) A dedicated PostgreSQL database/service for Polaris (Recommended)

B) A separate database in the existing PostgreSQL service, isolated from Airflow and the old Hive schema

C) Another supported backend; specify it below

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 14 — What deployment target and service exposure are required?

A) Local Docker Compose on one developer machine; bind admin UIs to loopback (Recommended based on the existing project)

B) A shared development host with LAN access and documented firewall rules

C) Production-like multi-host deployment with TLS and high availability

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 15 — What must pass before the first journey is accepted?

A) Clean bootstrap plus positive and negative tests: all catalogs/namespaces/buckets and test tables exist; each role has expected access and denied access; rerun is safe (Recommended)

B) Resource creation and positive access tests only

C) Resource creation plus manual verification by the platform admin

X) Other (please describe after [Answer]: tag below)

[Answer]:A

## Question 16 — Security Baseline Extension
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)

B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)

X) Other (please describe after [Answer]: tag below)

[Answer]:B

## Question 17 — Property-Based Testing Extension
Should property-based testing (PBT) rules be enforced for this project?

A) Yes — enforce all PBT rules as blocking constraints (recommended for projects with business logic, data transformations, serialization, or stateful components)

B) Partial — enforce PBT rules only for pure functions and serialization round-trips (suitable for projects with limited algorithmic complexity)

C) No — skip all PBT rules (suitable for simple CRUD applications, UI-only projects, or thin integration layers with no significant business logic)

X) Other (please describe after [Answer]: tag below)

[Answer]:B

## Question 18 — Resiliency Baseline Extension
Should the resiliency baseline be applied to this project as directional design guidance? It does not certify production readiness or establish an availability/RTO/RPO target.

A) Yes — apply the resiliency baseline as directional best practices (recommended for business-critical workloads)

B) No — skip the resiliency baseline (suitable for PoCs, prototypes, and experimental projects)

X) Other (please describe after [Answer]: tag below)

[Answer]:B


## Question 19 — Which services should the initial Compose journey start?
You authorized adjusting Docker Compose so this journey starts only the necessary services. Creating and verifying one Iceberg table in each environment likely requires a short-lived Spark bootstrap job in addition to the identity, catalog, and object-store services.

A) Start Keycloak, Polaris, its metadata database, RustFS, bootstrap helpers, and a short-lived Spark job for the three test tables; keep Airflow, JupyterHub, Jenkins, and StarRocks out of this journey's default startup (Recommended)

B) Start only Keycloak, Polaris, its metadata database, RustFS, and their bootstrap helpers; defer table creation/verification until Spark integration

C) Include one or more additional services in the first journey; name them below

X) Other (please describe after [Answer]: tag below)

[Answer]:A
